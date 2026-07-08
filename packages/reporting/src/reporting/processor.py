import logging
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any

import pandas as pd
from nepalidates import FilingMonth
from shared import SharedSettings
from shared.constants import (
    CANCELLED_STATUS,
    FUEL_ITEMS,
    CommonReportType,
    TransactionType,
)

from .excel_exporter import ExcelExporter
from .models import CompanyInfo, ReportHeaderDetails
from .report_configs import ReportConfig, ReportConfigs

logger = logging.getLogger(__name__)
settings = SharedSettings()


# --- Helper Function for Data Cleaning ---
def _clean_and_prepare_dataframe(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Performs initial data cleaning and type conversions."""
    transactions_df = (
        transactions_df.copy()
    )  # Work on a copy to avoid SettingWithCopyWarning

    # Convert columns to appropriate numeric types
    numeric_cols = [
        "In",
        "Out",
        "Grand Total",
        "Round Off",
        "Item Total",
        "VATABLE AMOUNT",
        "VAT AMOUNT",
    ]
    for col in numeric_cols:
        # Use errors='coerce' to turn unparseable values into NaN
        # Then fill NaN with 0 or a sensible default if appropriate for aggregation
        transactions_df[col] = pd.to_numeric(
            transactions_df[col],
            errors="coerce",
        ).fillna(0)

    # Convert 'Bill Date' to datetime for time-based analysis
    transactions_df["Bill Date"] = pd.to_datetime(
        transactions_df["Bill Date"],
        errors="coerce",
    )

    # Create a lowercase version of 'Inventory Name' for easier filtering
    transactions_df["Inventory Name Lower"] = (
        transactions_df["Inventory Name"].str.lower().fillna("")
    )

    # Fill 'Why Update' with empty string if NaN, to avoid issues with string operations
    if "Why Update" in transactions_df.columns:
        transactions_df["Why Update"] = transactions_df["Why Update"].fillna("")
    else:
        transactions_df["Why Update"] = ""  # Add column if it doesn't exist

    return transactions_df


# --- Report Dataframe Generation ---


class BaseReport(ABC):
    """
    Abstract base class for all reports, providing common structure and enforcing an interface.

    It accepts a ReportConfig object during initialization.
    """

    def __init__(
        self,
        config: ReportConfig,
        filing_month: FilingMonth,
        company_info: CompanyInfo,
    ):
        self.config = config
        self.name = config.name.name
        self.sheet_name = config.sheet_name
        self.filing_month = filing_month
        self.company_info = company_info
        self.processed_dataframe: pd.DataFrame = pd.DataFrame()

    @abstractmethod
    def generate_dataframe(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Abstract method to be implemented by subclasses to generate the specific report DataFrame."""

    def process_raw_data(self, raw_df: pd.DataFrame) -> None:
        """
        Cleans and processes the raw DataFrame and stores the result.

        This method should be called before attempting to export.
        """
        processed_df = _clean_and_prepare_dataframe(raw_df)
        self.processed_dataframe = self.generate_dataframe(processed_df)
        logger.info("DataFrame generated for %s report.", self.config.name)

    def _get_report_header_info(self) -> ReportHeaderDetails:
        """
        Constructs and returns a ReportHeaderDetails object containing company information and filing period details.

        Returns:
            ReportHeaderDetails: An object populated with company information, filing year, and filing month name.

        """
        return ReportHeaderDetails(
            **self.company_info.model_dump(),
            year=self.filing_month.year,
            month_name=self.filing_month.name,
        )

    def export_to_excel(self, template_buffer: BytesIO) -> BytesIO:
        """
        Exports the processed report data to an Excel file using the ExcelExporter.

        Args:
            template_buffer (BytesIO): A BytesIO buffer containing the Excel template.

        Returns:
            BytesIO: A BytesIO buffer containing the completed Excel file.

        Raises:
            ValueError: If the processed DataFrame is empty.
            Exception: For errors during the export process.

        """
        if self.processed_dataframe.empty:
            logger.error(
                "No processed data available for %s report. Call process_raw_data() first.",
                self.config.name,
            )
            msg = f"No data available for {self.config.name} Excel export."
            raise ValueError(msg)

        exporter = ExcelExporter()  # Instantiate the exporter
        report_header_details = self._get_report_header_info()

        logger.info("Exporting %s report to Excel.", self.config.name)
        try:
            return exporter.export_report_to_excel(
                report_type=self.config.name,
                template_buffer=template_buffer,
                report_header_info=report_header_details,
                transaction_df=self.processed_dataframe,
                sheet_name=self.sheet_name,
            )
        except Exception:
            logger.exception("Failed to export %s report to Excel.", self.config.name)
            raise

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"


class TransactionBasedReport(BaseReport):
    """Base class for reports that aggregate data based on transactions and items, like Purchase and Sales."""

    def __init__(
        self,
        config: ReportConfig,
        transaction_type: int,
        filing_month: FilingMonth,
        company_info: CompanyInfo,
    ):
        super().__init__(
            config=config,
            filing_month=filing_month,
            company_info=company_info,
        )
        self.transaction_type = transaction_type
        self.report_columns = config.report_columns

    def _insert_gap_columns(
        self,
        report_df: pd.DataFrame,
        column_template: list[str],
    ) -> pd.DataFrame:
        """
        Inserts empty columns into a DataFrame based on a column template containing '__gap__' placeholders.

        Args:
            report_df (pd.DataFrame): The DataFrame to modify.
            column_template (list[str]): A list of column names, which may include
                                         '__gap__' strings where empty columns are desired.

        Returns:
            pd.DataFrame: A new DataFrame with the specified gap columns inserted
                          and ordered according to the template.

        """
        processed_df = report_df.copy()
        final_columns = []

        # Keep track of generated gap column names to ensure uniqueness
        gap_counter = 0

        for col_name in column_template:
            if col_name == "__gap__":
                # Create a unique temporary name for the gap column
                gap_col_name = f"__GAP_COL_{gap_counter}__"
                # Add the new column to the DataFrame, filled with empty strings
                processed_df[gap_col_name] = ""
                final_columns.append(gap_col_name)
                gap_counter += 1
            else:
                # For actual data columns, ensure they exist before adding to final_columns
                # This check can help catch typos in column_template if a column is missing
                if col_name not in processed_df.columns:
                    logger.warning(
                        "Column '%s' not found in DataFrame. It will appear as empty.",
                        col_name,
                    )

                    # Add it as an empty column if it's missing
                    processed_df[col_name] = ""
                final_columns.append(col_name)

        # Select and reorder columns according to the final_columns list
        # This will include the original data columns and the newly added gap columns
        return processed_df[final_columns]

    def generate_dataframe(self, full_processed_df: pd.DataFrame) -> pd.DataFrame:
        """Generates the DataFrame for transaction-based reports (Purchase/Sales)."""
        non_cancelled_df = full_processed_df[
            full_processed_df["Status"] != CANCELLED_STATUS
        ].copy()

        filtered_transactions_df = non_cancelled_df[
            non_cancelled_df["Transaction Type"] == self.transaction_type
        ].copy()

        if filtered_transactions_df.empty:
            logger.info(
                "No transactions of type %s found for the period (%s).",
                self.transaction_type,
                self.name,
            )
            return pd.DataFrame(columns=self.config.report_columns)

        # Common aggregation logic
        report_df = filtered_transactions_df.groupby(
            [
                "Bill Date",
                "Transaction Date",
                "Nepali Date",
                "Transaction ID",
                "Bill Receiveable Person",
                "Vat Pan No",
                "Symbol",
                "Grand Total",
                "Round Off",
                "Reference No",
                "Status",
                "Transaction Type",
            ],
            as_index=False,
        ).agg(
            Item=("Inventory Name", lambda x: "/".join(sorted(x.astype(str).unique()))),
            Total_In_Quantity=("In", "sum"),
            Total_Out_Quantity=("Out", "sum"),
            Total_VATABLE_AMOUNT=("VATABLE AMOUNT", "sum"),
            Total_VAT_AMOUNT=("VAT AMOUNT", "sum"),
            Total_Item_Amount=("Item Total", "sum"),
        )
        return self._insert_gap_columns(
            report_df=report_df,
            column_template=self.report_columns,
        )


class PurchaseReport(TransactionBasedReport):
    def __init__(self, filing_month: FilingMonth, company_info: CompanyInfo):
        config = ReportConfigs.PURCHASE.value
        super().__init__(
            config=config,
            transaction_type=TransactionType.PURCHASE.value,
            filing_month=filing_month,
            company_info=company_info,
        )


class SalesReport(TransactionBasedReport):
    def __init__(self, filing_month: FilingMonth, company_info: CompanyInfo):
        config = ReportConfigs.SALES.value
        super().__init__(
            config=config,
            transaction_type=TransactionType.SALES.value,
            filing_month=filing_month,
            company_info=company_info,
        )


class LakhTransactionsReport(BaseReport):
    def __init__(self, filing_month: FilingMonth, company_info: CompanyInfo):
        config = ReportConfigs.LAKH_TRANSACTIONS.value
        super().__init__(
            config=config,
            filing_month=filing_month,
            company_info=company_info,
        )

    def generate_dataframe(self, full_processed_df: pd.DataFrame) -> pd.DataFrame:
        """Generates the DataFrame for Lakh+ transactions report."""
        if full_processed_df.empty:
            return pd.DataFrame(columns=self.config.report_columns)

        non_cancelled_df = full_processed_df[
            full_processed_df["Status"] != CANCELLED_STATUS
        ].copy()

        pan_transactions_df = non_cancelled_df[
            non_cancelled_df["Vat Pan No"].notna()
            & (non_cancelled_df["Vat Pan No"].astype(str).str.strip() != "")
        ].copy()

        if pan_transactions_df.empty:
            logger.info(
                "No transactions with Vat Pan No found for the period (Lakh+ Report).",
            )
            return pd.DataFrame(columns=self.config.report_columns)

        pan_transactions_df["Symbol"] = pan_transactions_df["Transaction Type"].map(
            {t.value: t.symbol for t in TransactionType},
        )

        transaction_level_summary = pan_transactions_df.groupby(
            "Transaction ID",
            as_index=False,
        ).agg(
            Transaction_Grand_Total=("Grand Total", "first"),
            Transaction_VATABLE_AMOUNT_Sum=("VATABLE AMOUNT", "sum"),
            Transaction_VAT_AMOUNT_Sum=("VAT AMOUNT", "sum"),
            Transaction_Vat_Pan_No=("Vat Pan No", "first"),
            Transaction_Bill_Receiveable_Person=("Bill Receiveable Person", "first"),
            Transaction_Symbol=("Symbol", "first"),
        )

        pan_summary_df = transaction_level_summary.groupby(
            ["Transaction_Vat_Pan_No", "Transaction_Symbol"],
            as_index=False,
        ).agg(
            Bill_Receiveable_Person=("Transaction_Bill_Receiveable_Person", "first"),
            Cumulative_Grand_Total=("Transaction_Grand_Total", "sum"),
            Cumulative_VATABLE_AMOUNT=("Transaction_VATABLE_AMOUNT_Sum", "sum"),
            Cumulative_VAT_AMOUNT=("Transaction_VAT_AMOUNT_Sum", "sum"),
            Number_of_Transactions=("Transaction ID", "nunique"),
        )

        lakh_report_df = pan_summary_df[
            pan_summary_df["Cumulative_Grand_Total"]
            > settings.HIGH_VALUE_TRANSACTION_THRESHOLD
        ].copy()

        if lakh_report_df.empty:
            logger.info(
                "No Vat Pan No groups found with cumulative Grand Total above %s.",
                f"{settings.HIGH_VALUE_TRANSACTION_THRESHOLD:,.2f}",
            )
            return pd.DataFrame(columns=self.config.report_columns)

        lakh_report_df = lakh_report_df.rename(
            columns={"Transaction_Vat_Pan_No": "Vat Pan No"},
        )

        lakh_report_df["Trade Name Type"] = "E"
        lakh_report_df["Exempted Amount"] = 0

        lakh_report_df["Transaction Type Symbol"] = lakh_report_df["Transaction_Symbol"]

        return lakh_report_df[self.config.report_columns].sort_values(
            by="Cumulative_VATABLE_AMOUNT",
            ascending=False,
        )


# --- Summary Analytics Generation ---


def _extract_core_dataframes(
    full_processed_df: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.Series,
    pd.Series,
]:
    """
    Extracts and prepares core dataframes and pre-computations needed for summary analytics.

    Returns non_cancelled_df, cancelled_df, purchase_df, sales_df,
    unique_purchase_transactions, unique_sales_transactions,
    total_purchase_vat_amounts, total_sales_vat_amounts.
    """
    non_cancelled_df = full_processed_df[
        full_processed_df["Status"] != CANCELLED_STATUS
    ]
    cancelled_df = full_processed_df[full_processed_df["Status"] == CANCELLED_STATUS]

    purchase_df = non_cancelled_df[
        non_cancelled_df["Transaction Type"] == TransactionType.PURCHASE.value
    ]
    sales_df = non_cancelled_df[
        non_cancelled_df["Transaction Type"] == TransactionType.SALES.value
    ]

    # Pre-computation: Transaction-level unique data for Grand Total, Round Off
    unique_purchase_transactions = purchase_df.drop_duplicates(subset="Transaction ID")
    unique_sales_transactions = sales_df.drop_duplicates(subset="Transaction ID")

    # Pre-computation: Item-level data for VAT amounts
    total_purchase_vat_amounts = purchase_df[["VATABLE AMOUNT", "VAT AMOUNT"]].sum()
    total_sales_vat_amounts = sales_df[["VATABLE AMOUNT", "VAT AMOUNT"]].sum()

    return (
        non_cancelled_df,
        cancelled_df,
        purchase_df,
        sales_df,
        unique_purchase_transactions,
        unique_sales_transactions,
        total_purchase_vat_amounts,
        total_sales_vat_amounts,
    )


def _calculate_financial_summary_metrics(
    summary: dict[str, Any],
    unique_purchase_transactions: pd.DataFrame,
    unique_sales_transactions: pd.DataFrame,
    total_purchase_vat_amounts: pd.Series,
    total_sales_vat_amounts: pd.Series,
) -> None:
    """Calculates and updates financial summary metrics in the summary dictionary."""
    summary["Total Grand Purchase Amount"] = unique_purchase_transactions[
        "Grand Total"
    ].sum()
    summary["Total Grand Sales Amount"] = unique_sales_transactions["Grand Total"].sum()

    # --- Add transactions count analytics ---
    summary["Purchase Transactions Count"] = unique_purchase_transactions.shape[0]
    summary["Sales Transactions Count"] = unique_sales_transactions.shape[0]

    purchase_tax_amount = total_purchase_vat_amounts.get("VAT AMOUNT", 0)
    sales_tax_amount = total_sales_vat_amounts.get("VAT AMOUNT", 0)

    summary["Total Purchase Taxable Amount"] = total_purchase_vat_amounts.get(
        "VATABLE AMOUNT",
        0,
    )
    summary["Total Purchase Tax Amount"] = purchase_tax_amount

    summary["Total Sales Taxable Amount"] = total_sales_vat_amounts.get(
        "VATABLE AMOUNT",
        0,
    )
    summary["Total Sales Tax Amount"] = sales_tax_amount

    summary["Net VAT Payable/Refundable"] = sales_tax_amount - purchase_tax_amount

    summary["Total Sales Round Off"] = unique_sales_transactions["Round Off"].sum()
    summary["Total Purchase Round Off"] = unique_purchase_transactions[
        "Round Off"
    ].sum()


def _calculate_fuel_quantities(
    summary: dict[str, Any],
    purchase_df: pd.DataFrame,
    sales_df: pd.DataFrame,
) -> None:
    """Calculates and updates fuel and goods quantities in the summary dictionary."""
    purchase_in_quantities = purchase_df.groupby("Inventory Name Lower")["In"].sum()
    sales_out_quantities = sales_df.groupby("Inventory Name Lower")["Out"].sum()

    # Common items for specific "other fuel" calculation
    other_fuel_items_specific = [
        item for item in FUEL_ITEMS if item not in ["petrol", "diesel"]
    ]

    summary["Petrol Purchase Quantity"] = purchase_in_quantities.get("petrol", 0)
    summary["Diesel Purchase Quantity"] = purchase_in_quantities.get("diesel", 0)
    summary["Other Fuel Purchase Quantity"] = (
        purchase_in_quantities[
            purchase_in_quantities.index.isin(other_fuel_items_specific)
        ].sum()
        if not purchase_in_quantities.empty
        else 0
    )
    non_fuel_purchase_df = purchase_df[
        ~purchase_df["Inventory Name Lower"].isin(FUEL_ITEMS)
    ]
    summary["Other Goods Purchase Quantity"] = non_fuel_purchase_df["In"].sum()

    summary["Petrol Sales Quantity"] = sales_out_quantities.get("petrol", 0)
    summary["Diesel Sales Quantity"] = sales_out_quantities.get("diesel", 0)
    summary["Other Fuel Sales Quantity"] = (
        sales_out_quantities[
            sales_out_quantities.index.isin(other_fuel_items_specific)
        ].sum()
        if not sales_out_quantities.empty
        else 0
    )
    non_fuel_sales_df = sales_df[~sales_df["Inventory Name Lower"].isin(FUEL_ITEMS)]
    summary["Other Goods Sales Quantity"] = non_fuel_sales_df["Out"].sum()


def _get_top_transactions_data(
    summary: dict[str, Any],
    unique_purchase_transactions: pd.DataFrame,
    unique_sales_transactions: pd.DataFrame,
) -> None:
    """Calculates and updates top 5 transactions in the summary dictionary."""
    summary["Top 5 Purchase Transactions"] = unique_purchase_transactions.nlargest(
        5,
        "Grand Total",
    )[
        ["Bill Date", "Transaction ID", "Bill Receiveable Person", "Grand Total"]
    ].to_dict(orient="records")

    summary["Top 5 Sales Transactions"] = unique_sales_transactions.nlargest(
        5,
        "Grand Total",
    )[
        ["Bill Date", "Transaction ID", "Bill Receiveable Person", "Grand Total"]
    ].to_dict(orient="records")


def _get_top_customer_supplier_item_data(
    summary: dict[str, Any],
    purchase_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    unique_purchase_transactions: pd.DataFrame,
    unique_sales_transactions: pd.DataFrame,
) -> None:
    """Calculates and updates top customers, suppliers, and items in the summary dictionary."""
    summary["Top 5 Sales Customers"] = (
        unique_sales_transactions.groupby("Bill Receiveable Person")["Grand Total"]
        .sum()
        .nlargest(5)
        .to_dict()
    )
    summary["Top 5 Purchase Suppliers"] = (
        unique_purchase_transactions.groupby("Bill Receiveable Person")["Grand Total"]
        .sum()
        .nlargest(5)
        .to_dict()
    )

    summary["Top 5 Sales Items"] = (
        sales_df.groupby("Inventory Name")["Item Total"].sum().nlargest(5).to_dict()
    )
    summary["Top 5 Purchase Items"] = (
        purchase_df.groupby("Inventory Name")["Item Total"].sum().nlargest(5).to_dict()
    )


def _process_cancelled_transactions_data(
    summary: dict[str, Any],
    cancelled_df: pd.DataFrame,
) -> None:
    """Processes and updates cancelled transactions data in the summary dictionary."""
    if not cancelled_df.empty:
        cancelled_summary = cancelled_df.groupby("Transaction ID", as_index=False).agg(
            Transaction_Grand_Total=("Grand Total", "first"),
            Transaction_Type=("Transaction Type", "first"),
            Bill_Receiveable_Person=("Bill Receiveable Person", "first"),
            Why_Update=(
                "Why Update",
                lambda x: "/ ".join(x.astype(str).unique()) if x.any() else "N/A",
            ),
            Cancellation_Date=("Bill Date", "first"),
        )

        cancelled_summary["Transaction_Type_Symbol"] = cancelled_summary[
            "Transaction_Type"
        ].apply(
            lambda x: TransactionType(x).symbol
            if x in [item.value for item in TransactionType]
            else "N/A",
        )

        summary["Total Cancelled Transactions"] = cancelled_summary.shape[0]
        summary["Cancelled Transactions List"] = cancelled_summary[
            [
                "Cancellation_Date",
                "Transaction ID",
                "Bill_Receiveable_Person",
                "Transaction_Type_Symbol",
                "Transaction_Grand_Total",
                "Why_Update",
            ]
        ].to_dict(orient="records")
    else:
        summary["Total Cancelled Transactions"] = 0
        summary["Cancelled Transactions List"] = []


def generate_summary_analytics(raw_transactions_df: pd.DataFrame) -> dict[str, Any]:
    """
    Generates a dictionary containing all summary analytics after cleaning and preparing the raw transaction dataframe internally.

    This function orchestrates calls to smaller, focused helper functions for improved readability and maintainability.

    Args:
        raw_transactions_df (pd.DataFrame): The raw, unprocessed transaction dataframe.

    Returns:
        Dict[str, Any]: A dictionary containing all calculated summary analytics.

    """
    summary: dict[str, Any] = {}

    full_processed_df = _clean_and_prepare_dataframe(raw_transactions_df)

    (
        non_cancelled_df,
        cancelled_df,
        purchase_df,
        sales_df,
        unique_purchase_transactions,
        unique_sales_transactions,
        total_purchase_vat_amounts,
        total_sales_vat_amounts,
    ) = _extract_core_dataframes(full_processed_df)

    if non_cancelled_df.empty:
        # Populate summary with zeros/empty lists if no non-cancelled data
        summary.update(
            {
                "Total Grand Purchase Amount": 0,
                "Total Grand Sales Amount": 0,
                "Petrol Purchase Quantity": 0,
                "Diesel Purchase Quantity": 0,
                "Other Fuel Purchase Quantity": 0,
                "Other Goods Purchase Quantity": 0,
                "Petrol Sales Quantity": 0,
                "Diesel Sales Quantity": 0,
                "Other Fuel Sales Quantity": 0,
                "Other Goods Sales Quantity": 0,
                "Net VAT Payable/Refundable": 0,
                "Top 5 Purchase Transactions": [],
                "Top 5 Sales Transactions": [],
                "Top 5 Sales Customers": {},
                "Top 5 Purchase Suppliers": {},
                "Total Purchase Taxable Amount": 0,
                "Total Purchase Tax Amount": 0,
                "Total Sales Taxable Amount": 0,
                "Total Sales Tax Amount": 0,
                "Top 5 Sales Items": {},
                "Top 5 Purchase Items": {},
                "Total Sales Round Off": 0,
                "Total Purchase Round Off": 0,
                # --- Add analytics keys with zero ---
                "Purchase Transactions Count": 0,
                "Sales Transactions Count": 0,
            },
        )
    else:
        _calculate_financial_summary_metrics(
            summary,
            unique_purchase_transactions,
            unique_sales_transactions,
            total_purchase_vat_amounts,
            total_sales_vat_amounts,
        )
        _calculate_fuel_quantities(summary, purchase_df, sales_df)
        _get_top_transactions_data(
            summary,
            unique_purchase_transactions,
            unique_sales_transactions,
        )
        _get_top_customer_supplier_item_data(
            summary,
            purchase_df,
            sales_df,
            unique_purchase_transactions,
            unique_sales_transactions,
        )

    _process_cancelled_transactions_data(summary, cancelled_df)

    return summary


def process_and_export_reports(
    raw_transactions_df: pd.DataFrame,
    filing_month: FilingMonth,
    company_info: CompanyInfo,
    downloaded_templates: dict[CommonReportType, BytesIO],
) -> dict[CommonReportType, BytesIO]:
    """
    Processes raw transactions and exports Purchase, Sales, and Lakh Transactions reports to Excel buffers.

    Args:
        raw_transactions_df: DataFrame containing raw transaction data.
        filing_month: FilingMonth instance for the report period.
        company_info: CompanyInfo DTO.
        downloaded_templates: Dictionary of BytesIO buffers for report templates.

    Returns:
        A dictionary mapping CommonReportType to BytesIO buffer of the exported Excel report.

    """
    if raw_transactions_df.empty:
        logger.warning("Raw data is empty. No reports will be processed or exported.")
        return {}

    exported_reports_buffers: dict[CommonReportType, BytesIO] = {}

    report_classes_and_types = [
        (PurchaseReport, CommonReportType.PURCHASE),
        (SalesReport, CommonReportType.SALES),
        (LakhTransactionsReport, CommonReportType.LAKH_TRANSACTIONS),
    ]

    for ReportClass, report_type in report_classes_and_types:  # noqa: N806
        logger.info("--- Processing and Exporting %s Report ---", report_type.name)
        report_instance: TransactionBasedReport = ReportClass(
            filing_month=filing_month,
            company_info=company_info,
        )
        report_instance.process_raw_data(raw_transactions_df)

        if report_instance.processed_dataframe.empty:
            logger.warning("%s DataFrame is empty, skipping export.", report_type.name)
            continue

        template_buffer = downloaded_templates.get(report_type)
        if not template_buffer:
            logger.error(
                "Failed to get %s template. Cannot export report.",
                report_type.name,
            )
            continue

        try:
            exported_excel_buffer = report_instance.export_to_excel(
                template_buffer=template_buffer,
            )
            exported_reports_buffers[report_type] = exported_excel_buffer
            logger.info(
                "%s Report successfully processed and exported to buffer.",
                report_type.name,
            )
        except Exception:
            logger.exception(
                "Error processing or exporting %s report.",
                report_type.name,
            )

    return exported_reports_buffers
