"""Fiscal year workflow orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import pandas as pd
from dbkit.engine import get_engine
from nepalidates import FilingMonth
from reporting.fetcher import fetch_raw_transaction_dataframe
from reporting.fiscal_year import FiscalYearRange
from shared import SharedSettings

logger = logging.getLogger(__name__)


def _consolidate_purchase_and_sales(
    raw_data_by_month: Dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Consolidate monthly transaction data into purchase and sales DataFrames.

    Differentiates between purchase and sales based on the 'Transaction Type' column:
    - Transaction Type = 1: Purchase
    - Transaction Type = 2: Sales

    Filters to only include valid transactions with Status = '001-00'.
    Discards canceled or invalid transactions with other status codes.

    Args:
        raw_data_by_month: Dictionary mapping month names to transaction DataFrames

    Returns:
        Tuple of (purchase_df, sales_df) consolidated across all months
    """
    all_transactions = []

    for month_name, month_df in raw_data_by_month.items():
        month_df_copy = month_df.copy()
        month_df_copy["reporting_period"] = month_name
        all_transactions.append(month_df_copy)

    # Combine all monthly transactions
    consolidated_df = pd.concat(all_transactions, ignore_index=True)

    if consolidated_df.empty:
        logger.warning("No consolidated transactions to process")
        return pd.DataFrame(), pd.DataFrame()

    # Filter to only valid transactions with Status '001-00'
    # Discard canceled or invalid transactions (other status codes)
    initial_count = len(consolidated_df)
    consolidated_df = consolidated_df[consolidated_df["Status"] == "001-00"].copy()
    filtered_count = initial_count - len(consolidated_df)

    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count} canceled/invalid transactions")

    if consolidated_df.empty:
        logger.warning("No valid transactions after status filtering")
        return pd.DataFrame(), pd.DataFrame()

    # Differentiate purchase vs sales based on Transaction Type column
    # Transaction Type 1 = PURCHASE, 2 = SALES
    purchase_df = consolidated_df[consolidated_df["Transaction Type"] == 1].copy()
    sales_df = consolidated_df[consolidated_df["Transaction Type"] == 2].copy()

    logger.info(
        f"Consolidated transactions: {len(purchase_df)} purchases, {len(sales_df)} sales"
    )

    return purchase_df, sales_df


def _save_consolidated_excel(
    purchase_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    fiscal_range: FiscalYearRange,
    settings: SharedSettings,
) -> tuple[str, str]:
    """
    Save consolidated purchase and sales data to Excel files.

    Args:
        purchase_df: Consolidated purchase transactions
        sales_df: Consolidated sales transactions
        fiscal_range: The fiscal year range being processed
        settings: Application settings

    Returns:
        Tuple of (purchase_file_path, sales_file_path)
    """
    output_dir = Path(settings.DEFAULT_REPORTS_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filenames with fiscal year range
    period_label = (
        f"{fiscal_range.start_month.year}-{fiscal_range.start_month.month:02d}_to_"
        f"{fiscal_range.end_month.year}-{fiscal_range.end_month.month:02d}"
    )

    purchase_file = output_dir / f"consolidated_purchases_{period_label}.xlsx"
    sales_file = output_dir / f"consolidated_sales_{period_label}.xlsx"

    # Write purchase data
    if not purchase_df.empty:
        with pd.ExcelWriter(purchase_file, engine="openpyxl") as writer:
            purchase_df.to_excel(
                writer,
                sheet_name="Purchases",
                index=False,
                freeze_panes=(1, 0),
            )
            # Add summary sheet
            purchase_summary = pd.DataFrame(
                {
                    "Metric": [
                        "Total Transactions",
                        "Total Amount",
                        "Total Taxable Amount",
                        "Total Tax Amount",
                        "Reporting Period",
                    ],
                    "Value": [
                        len(purchase_df),
                        purchase_df.get("Grand Total", pd.Series([0])).sum(),
                        purchase_df.get("VATABLE AMOUNT", pd.Series([0])).sum(),
                        purchase_df.get("VAT AMOUNT", pd.Series([0])).sum(),
                        f"{fiscal_range.start_month.name} to {fiscal_range.end_month.name}",
                    ],
                }
            )
            purchase_summary.to_excel(
                writer,
                sheet_name="Summary",
                index=False,
            )
        logger.info(f"Saved purchase data to {purchase_file}")
    else:
        logger.warning("No purchase data to save")

    # Write sales data
    if not sales_df.empty:
        with pd.ExcelWriter(sales_file, engine="openpyxl") as writer:
            sales_df.to_excel(
                writer,
                sheet_name="Sales",
                index=False,
                freeze_panes=(1, 0),
            )
            # Add summary sheet
            sales_summary = pd.DataFrame(
                {
                    "Metric": [
                        "Total Transactions",
                        "Total Amount",
                        "Total Taxable Amount",
                        "Total Tax Amount",
                        "Reporting Period",
                    ],
                    "Value": [
                        len(sales_df),
                        sales_df.get("Grand Total", pd.Series([0])).sum(),
                        sales_df.get("VATABLE AMOUNT", pd.Series([0])).sum(),
                        sales_df.get("VAT AMOUNT", pd.Series([0])).sum(),
                        f"{fiscal_range.start_month.name} to {fiscal_range.end_month.name}",
                    ],
                }
            )
            sales_summary.to_excel(
                writer,
                sheet_name="Summary",
                index=False,
            )
        logger.info(f"Saved sales data to {sales_file}")
    else:
        logger.warning("No sales data to save")

    return str(purchase_file), str(sales_file)


def execute_fiscal_year_workflow(  # noqa: PLR0913
    fiscal_range: FiscalYearRange,
    settings: SharedSettings,
    *,
    dry_run: bool = False,
    output_analytics_to_console: bool = True,
    save_analytics_html_locally: bool = True,
    upload_to_gdrive: bool = False,
    send_email: bool = False,
    save_excel_locally: bool = True,
) -> None:
    """
    Execute the fiscal year report generation workflow.

    This workflow consolidates transactions from multiple months into purchase
    and sales Excel files without using individual templates.

    Args:
        fiscal_range: FiscalYearRange specifying the period to process
        settings: Application settings
        dry_run: If True, simulate without making changes
        output_analytics_to_console: Whether to print analytics to console
        save_analytics_html_locally: Whether to save HTML reports locally
        upload_to_gdrive: Whether to upload to Google Drive
        send_email: Whether to send email with reports
        save_excel_locally: Whether to save Excel files locally
    """
    if dry_run:
        logger.info("[DRY RUN] Running in simulation mode")
        return

    # Step 1: Fetch data for all months in range
    raw_data_by_month: Dict[str, pd.DataFrame] = {}
    engine = get_engine(settings.TARGET_DATABASE)

    current_month = fiscal_range.start_month
    while current_month <= fiscal_range.end_month:
        logger.info(f"Fetching data for {current_month.name}")

        monthly_data = fetch_raw_transaction_dataframe(
            engine, current_month.ad_date_range.start, current_month.ad_date_range.end
        )

        if not monthly_data.empty:
            raw_data_by_month[current_month.name] = monthly_data
            logger.info(
                f"Found {len(monthly_data)} transactions for {current_month.name}"
            )
        else:
            logger.warning(f"No transactions found for {current_month.name}")

        current_month = current_month.next()

    if not raw_data_by_month:
        logger.error("No transaction data found for any month in range")
        return

    # Step 2: Consolidate purchase and sales data
    logger.info("Consolidating purchase and sales transactions")
    purchase_df, sales_df = _consolidate_purchase_and_sales(raw_data_by_month)

    if purchase_df.empty and sales_df.empty:
        logger.error("No purchase or sales data to process")
        return

    purchase_file, sales_file = "", ""
    if save_excel_locally:
        logger.info("Saving consolidated data to Excel files")
        purchase_file, sales_file = _save_consolidated_excel(
            purchase_df,
            sales_df,
            fiscal_range,
            settings,
        )

    # Step 3: Handle additional outputs based on flags
    if output_analytics_to_console:
        logger.info(f"Purchase Summary: {len(purchase_df)} transactions")
        logger.info(f"Sales Summary: {len(sales_df)} transactions")
        if not purchase_df.empty:
            logger.info(
                f"  Purchase Total Amount: {purchase_df.get('Grand Total', pd.Series([0])).sum():,.2f}"
            )
        if not sales_df.empty:
            logger.info(
                f"  Sales Total Amount: {sales_df.get('Grand Total', pd.Series([0])).sum():,.2f}"
            )

    if save_analytics_html_locally:
        # TODO: Implement HTML save logic for consolidated data
        pass

    if upload_to_gdrive:
        # TODO: Implement GDrive upload logic for purchase/sales files
        logger.info(f"To upload: {purchase_file} and {sales_file}")

    if send_email:
        # TODO: Implement email logic with purchase/sales file attachments
        logger.info(f"To email: {purchase_file} and {sales_file}")

    logger.info("Fiscal year workflow completed successfully")
