from __future__ import annotations

import logging
import sys
from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd
from dbkit.engine import get_engine
from downloader.manager import download_ird_templates, download_latest_mssql_backup
from file_operations.disk_writer import write_bytes_to_disk
from mailer.client import send_vat_report_email
from reporting.fetcher import fetch_raw_transaction_dataframe
from reporting.formatter import (
    ConsoleReportFormatter,
    HtmlReportFormatter,
)
from reporting.processor import (
    generate_summary_analytics,
    process_and_export_reports,
)
from restorer.restore import restore_database
from shared import SharedSettings
from shared.constants import CommonReportType
from shared.utils import get_company_info_from_args_or_settings
from uploader.manager import upload_reports_to_gdrive

if TYPE_CHECKING:
    from pathlib import Path

    from nepalidates import FilingMonth
    from reporting.models import CompanyInfo

# Note: LoggerFactory.configure_logging should be called once at the application's entry point (main.py)
# This module uses a standard logger, assuming the root logger is already configured.
logger = logging.getLogger(__name__)


def _download_and_restore_database(
    settings: SharedSettings,
    *,
    dry_run: bool,
) -> Path | None:
    """Handles the database backup download and restore steps."""
    local_backup_path: Path | None = None
    if dry_run:
        logger.info("[DRY RUN] Skipping database backup and restore.")
        return None

    try:
        logger.info("Attempting to download latest MSSQL backup...")
        # Note: download_latest_mssql_backup can save locally if specified, useful for restore.
        # We need the path inside the container for restore, so the path on host is not what we want here.
        # The logic for docker mounting might need more sophistication.
        # For now, let's assume the downloaded file is moved or accessible by the DB container.
        # For a truly dockerized env, this step often involves a separate docker volume mount.
        # Let's simplify: we download to a known shared location that the DB container can see.

        # If download_latest_mssql_backup can download *and* return the path within the DB mount
        # (e.g., if this is run inside a container with a shared volume or if the path is configured for the DB)
        # then we can use that directly. Otherwise, it's a more complex orchestration problem.

        # For this refactor, let's assume `download_latest_mssql_backup` saves to `settings.backup_dir`
        # and `restore_database` will receive a path that's valid *from the perspective of the DB server*.
        # This implies `settings.mssql_backup_mount` is the internal path where `settings.backup_dir` contents appear.

        local_backup_path = download_latest_mssql_backup()
        if not local_backup_path:
            logger.error(
                "Could not download latest MSSQL backup. Exiting workflow.",
            )
            sys.exit(1)
    except Exception:
        logger.exception("Error during backup download.")
        logger.error("CRITICAL: Could download file for restore. Exiting workflow.")  # noqa: TRY400
        sys.exit(1)

    if local_backup_path:
        mssql_container_backup_path = (
            settings.MSSQL_BACKUP_MOUNT / local_backup_path.name
        )
        try:
            logger.info("Restoring database from %s...", mssql_container_backup_path)
            restore_database(
                backup_path=mssql_container_backup_path,
                db_name=settings.TARGET_DATABASE,
            )
            logger.info("Database restore complete.")
        except Exception:
            logger.exception("Database restore failed.")
            logger.error("CRITICAL: Database restore failed. Exiting workflow.")  # noqa: TRY400
            sys.exit(1)  # Critical failure, exit
        else:
            return local_backup_path  # Return path if successful
    return None


def _fetch_transactions(
    settings: SharedSettings,
    filing_month: FilingMonth,
    *,
    dry_run: bool = False,
) -> pd.DataFrame:
    """Fetches raw transaction data."""
    if dry_run:
        logger.info("[DRY RUN] Skipping IRD template download.")
        return pd.DataFrame()
    logger.info("Fetching raw transaction data for %s...", filing_month.name)
    engine = get_engine(settings.TARGET_DATABASE)
    try:
        raw_transactions_df = fetch_raw_transaction_dataframe(
            engine,
            filing_month.ad_date_range.start,
            filing_month.ad_date_range.end,
        )
        if raw_transactions_df.empty:
            logger.warning(
                "No raw transactions found for %s. Reports will be empty.",
                filing_month.name,
            )
        else:
            logger.info(
                "Fetched %d raw transactions for %s.",
                len(raw_transactions_df),
                filing_month.name,
            )
    except Exception:
        logger.exception("Error fetching raw transaction data.")
        sys.exit(1)
    else:
        return raw_transactions_df


def _download_templates(
    settings: SharedSettings,
    *,
    dry_run: bool,
) -> dict[CommonReportType, BytesIO]:
    """Downloads IRD Excel templates."""
    if dry_run:
        logger.info("[DRY RUN] Skipping IRD template download.")
        return {}

    try:
        logger.info("Downloading IRD Excel templates...")
        downloaded_templates = download_ird_templates(
            template_types=[
                CommonReportType.PURCHASE,
                CommonReportType.SALES,
                CommonReportType.LAKH_TRANSACTIONS,
            ],
            save_locally=False,  # We use the buffer directly
            local_save_dir=settings.DEFAULT_DOWNLOAD_PATH,  # Still needed for function signature but not actively used for saving here
        )
        if not downloaded_templates:
            logger.error(
                "Failed to download any templates. Reports might not be generated.",
            )
    except Exception:
        logger.exception("Error downloading IRD templates.")
        sys.exit(1)
    else:
        return downloaded_templates


def _process_and_export_excel_reports(  # noqa: PLR0913
    raw_transactions_df: pd.DataFrame,
    filing_month: FilingMonth,
    company_info: CompanyInfo,
    downloaded_templates: dict[CommonReportType, BytesIO],
    settings: SharedSettings,
    *,
    dry_run: bool,
    save_excel_locally: bool = True,
) -> dict[CommonReportType, BytesIO]:
    """Processes transactions and exports reports to Excel, saving them locally if requested."""
    exported_excel_buffers: dict[CommonReportType, BytesIO] = {}
    if raw_transactions_df.empty or dry_run:
        logger.info(
            "[DRY RUN] Skipping report processing and export (no data or dry run).",
        )
        return {}

    if not company_info:
        logger.warning("Skipping report processing: Company information not available.")
        return {}

    logger.info("Processing and exporting reports...")
    try:
        exported_excel_buffers = process_and_export_reports(
            raw_transactions_df=raw_transactions_df,
            filing_month=filing_month,
            company_info=company_info,
            downloaded_templates=downloaded_templates,
        )

        # Save exported reports to disk if requested
        if save_excel_locally and not dry_run:
            for rtype, buffer in exported_excel_buffers.items():
                output_filepath = (
                    settings.DEFAULT_REPORTS_PATH
                    / filing_month.fiscal_year.replace("/", "-")
                    / filing_month.name
                    / f"{rtype.name} - {filing_month.name}{rtype.file_extension}"
                )
                try:
                    write_bytes_to_disk(buffer, output_filepath)
                    logger.info(
                        "Saved %s report to: %s",
                        rtype.name,
                        output_filepath.resolve(),
                    )
                except Exception:
                    logger.exception("Failed to save %s report locally.", rtype.name)
        elif not save_excel_locally:
            logger.info("Skipping saving Excel reports to disk as per flag.")

    except Exception:
        logger.exception("Error during report processing and export.")
    return exported_excel_buffers


def _generate_and_save_analytics(  # noqa: PLR0913
    raw_transactions_df: pd.DataFrame,
    filing_month: FilingMonth,
    settings: SharedSettings,
    *,
    output_to_console: bool,
    save_html_locally: bool,
    dry_run: bool,
) -> str | None:
    """Generates analytics, outputs to console, and saves HTML locally."""
    analytics_html_content: str | None = None

    if raw_transactions_df.empty:
        logger.info("Skipping analytics generation (no data).")
        return None

    logger.info("Generating analytics data...")
    try:
        analytics_summary_data = generate_summary_analytics(raw_transactions_df)

        if output_to_console:
            logger.info("Outputting analytics to console...")
            console_formatter = ConsoleReportFormatter(
                summary_data=analytics_summary_data,
                filing_month_name=filing_month.name,
            )
            console_output = console_formatter.format_report()
            print(console_output)

        logger.info("Generating analytics HTML content...")
        html_formatter = HtmlReportFormatter(
            summary_data=analytics_summary_data,
            filing_month_name=filing_month.name,
        )
        analytics_html_content = html_formatter.format_report()

        if save_html_locally and not dry_run:
            logger.info("Saving analytics HTML report locally...")
            html_buffer_for_disk = BytesIO(analytics_html_content.encode("utf-8"))
            html_filename_for_disk = f"summary_analytics_{filing_month.name}.html"

            html_report_filepath = (
                settings.DEFAULT_REPORTS_PATH
                / filing_month.fiscal_year.replace("/", "-")
                / filing_month.name
                / html_filename_for_disk
            )
            try:
                write_bytes_to_disk(html_buffer_for_disk, html_report_filepath)
                logger.info(
                    "Analytics HTML report saved to: %s",
                    html_report_filepath.resolve(),
                )
            except Exception:
                logger.exception("Failed to save analytics HTML report locally.")
        elif dry_run:
            logger.info("[DRY RUN] Skipping saving analytics HTML.")

    except Exception:
        logger.exception("Error generating or outputting analytics.")
        analytics_html_content = None  # Ensure it's None if generation failed

    return analytics_html_content


def _upload_reports(  # noqa: PLR0913
    exported_excel_buffers: dict[CommonReportType, BytesIO],
    analytics_html_content: str | None,
    filing_month: FilingMonth,
    company_info: CompanyInfo,
    *,
    upload_to_gdrive: bool,
    dry_run: bool,
) -> None:
    """Uploads reports to Google Drive."""
    if not upload_to_gdrive or dry_run:
        logger.info(
            "Skipping upload to Google Drive. (upload_to_gdrive=%s, dry_run=%s)",
            upload_to_gdrive,
            dry_run,
        )
        return

    logger.info("Uploading reports to Google Drive...")
    html_buffer_for_gdrive = (
        BytesIO(analytics_html_content.encode("utf-8"))
        if analytics_html_content
        else None
    )
    html_filename_for_gdrive = (
        f"summary_analytics_{filing_month.name}.html"
        if analytics_html_content
        else None
    )
    try:
        upload_reports_to_gdrive(
            exported_excel_reports=exported_excel_buffers,
            analytics_html_buffer=html_buffer_for_gdrive,
            analytics_html_filename=html_filename_for_gdrive,
            filing_month=filing_month,
            company_info=company_info,
        )
        logger.info("Reports uploaded to Google Drive successfully.")
    except Exception:
        logger.exception("Failed to upload reports to Google Drive.")


def _send_reports_email(  # noqa: PLR0913
    filing_month: FilingMonth,
    company_info: CompanyInfo,
    exported_excel_buffers: dict[CommonReportType, BytesIO],
    analytics_html_content: str | None,
    *,
    send_email: bool,
    dry_run: bool,
) -> None:
    """Sends an email with reports."""
    if not send_email or dry_run:
        logger.info(
            "Skipping email sending. (send_email=%s, dry_run=%s)", send_email, dry_run
        )
        return

    if not analytics_html_content:
        logger.warning(
            "Skipping email sending: Analytics HTML content is not available for the body.",
        )
        return

    logger.info("Sending email with reports...")
    try:
        send_vat_report_email(
            filing_month=filing_month,
            company_info=company_info,
            exported_excel_reports=exported_excel_buffers,
            analytics_html_content=analytics_html_content,
        )
        logger.info("Email with reports sent successfully.")
    except Exception:
        logger.exception("Failed to send email with reports")


def execute_vat_workflow(  # noqa: PLR0913
    filing_month: FilingMonth,
    pan: str | None = None,
    office_name: str | None = None,
    *,
    dry_run: bool = False,
    output_analytics_to_console: bool = True,
    save_analytics_html_locally: bool = True,
    upload_to_gdrive: bool = False,
    send_email: bool = False,
    save_excel_locally: bool = True,  # <-- add this parameter
) -> None:
    """
    Orchestrates the full VAT reporting workflow.

    Args:
        filing_month: The FilingMonth instance to process.
        pan: Optional PAN number override.
        office_name: Optional office name override.
        dry_run: If True, simulates the workflow without making permanent changes.
        output_analytics_to_console: Whether to print analytics summary to console.
        save_analytics_html_locally: Whether to save analytics HTML report to disk.
        upload_to_gdrive: Whether to upload generated reports and backups to Google Drive.
        send_email: Whether to send an email with reports.
        save_excel_locally: Whether to save generated Excel reports to disk.

    """
    settings = SharedSettings()

    logger.info(
        "Starting VAT Workflow for Filing Month: %s (Dry Run: %s)",
        filing_month.name,
        dry_run,
    )

    # Step 1: Get Company Info
    try:
        company_info = get_company_info_from_args_or_settings(
            pan=pan,
            office_name=office_name,
            settings=settings,
            logger_instance=logger,
        )
    except ValueError:
        logger.exception("Failed to get company information.")
        sys.exit(1)

    # Step 2 & 3: Download Latest Database Backup and Restore
    _download_and_restore_database(settings, dry_run=dry_run)

    # Step 4: Fetch Raw Transactions
    raw_transactions_df = _fetch_transactions(settings, filing_month, dry_run=dry_run)

    # Step 5: Download IRD Templates
    downloaded_templates = _download_templates(settings, dry_run=dry_run)

    # Step 6: Process and Export Reports to Excel
    exported_excel_buffers = _process_and_export_excel_reports(
        raw_transactions_df=raw_transactions_df,
        filing_month=filing_month,
        company_info=company_info,
        downloaded_templates=downloaded_templates,
        settings=settings,
        dry_run=dry_run,
        save_excel_locally=save_excel_locally,
    )

    # Step 7: Generate and Output Analytics Data
    analytics_html_content = _generate_and_save_analytics(
        raw_transactions_df=raw_transactions_df,
        filing_month=filing_month,
        settings=settings,
        output_to_console=output_analytics_to_console,
        save_html_locally=save_analytics_html_locally,
        dry_run=dry_run,
    )

    # Step 8: Upload Reports to Google Drive (if enabled)
    _upload_reports(
        exported_excel_buffers=exported_excel_buffers,
        analytics_html_content=analytics_html_content,
        filing_month=filing_month,
        company_info=company_info,
        upload_to_gdrive=upload_to_gdrive,
        dry_run=dry_run,
    )

    # Step 9: Send Email with Reports (if enabled)
    _send_reports_email(
        filing_month=filing_month,
        company_info=company_info,
        exported_excel_buffers=exported_excel_buffers,
        analytics_html_content=analytics_html_content,
        send_email=send_email,
        dry_run=dry_run,
    )

    logger.info("VAT Workflow Completed for Filing Month: %s", filing_month.name)


def execute_report_generation_workflow(  # noqa: PLR0913
    filing_month: FilingMonth,
    pan: str | None = None,
    office_name: str | None = None,
    *,
    dry_run: bool = False,
    output_analytics_to_console: bool = True,
    save_analytics_html_locally: bool = True,
    upload_to_gdrive: bool = False,
    send_email: bool = False,
    save_excel_locally: bool = True,
) -> None:
    """
    Orchestrates the VAT report generation workflow.

    Assumes the database is already restored and ready for data fetching.

    Args:
        filing_month: The FilingMonth instance to process.
        pan: Optional PAN number override.
        office_name: Optional office name override.
        dry_run: If True, simulates the workflow without making permanent changes.
        output_analytics_to_console: Whether to print analytics summary to console.
        save_analytics_html_locally: Whether to save analytics HTML report to disk.
        upload_to_gdrive: Whether to upload generated reports and backups to Google Drive.
        send_email: Whether to send an email with reports.
        save_excel_locally: Whether to save generated Excel reports to disk.

    """
    settings = SharedSettings()  # Needs to be initialized here as this is a standalone entry point for this workflow

    logger.info(
        "Starting Report Generation Workflow for Filing Month: %s (Dry Run: %s)",
        filing_month.name,
        dry_run,
    )

    company_info: CompanyInfo | None = None
    try:
        # Step 1: Get Company Info
        company_info = get_company_info_from_args_or_settings(
            pan=pan,
            office_name=office_name,
            settings=settings,
            logger_instance=logger,
        )
    except ValueError:
        logger.exception("Failed to get company information.")
        sys.exit(1)

    # Step 2: Fetch Raw Transactions
    raw_transactions_df = _fetch_transactions(settings, filing_month)

    # Step 3: Download IRD Templates
    downloaded_templates = _download_templates(settings, dry_run=dry_run)

    # Step 4: Process and Export Reports to Excel
    exported_excel_buffers = _process_and_export_excel_reports(
        raw_transactions_df=raw_transactions_df,
        filing_month=filing_month,
        company_info=company_info,
        downloaded_templates=downloaded_templates,
        settings=settings,
        dry_run=dry_run,
        save_excel_locally=save_excel_locally,
    )

    # Step 5: Generate and Output Analytics Data
    analytics_html_content = _generate_and_save_analytics(
        raw_transactions_df=raw_transactions_df,
        filing_month=filing_month,
        settings=settings,
        output_to_console=output_analytics_to_console,
        save_html_locally=save_analytics_html_locally,
        dry_run=dry_run,
    )

    # Step 6: Upload Reports to Google Drive (if enabled)
    _upload_reports(
        exported_excel_buffers=exported_excel_buffers,
        analytics_html_content=analytics_html_content,
        filing_month=filing_month,
        company_info=company_info,
        upload_to_gdrive=upload_to_gdrive,
        dry_run=dry_run,
    )

    # Step 7: Send Email with Reports (if enabled)
    _send_reports_email(
        filing_month=filing_month,
        company_info=company_info,
        exported_excel_buffers=exported_excel_buffers,
        analytics_html_content=analytics_html_content,
        send_email=send_email,
        dry_run=dry_run,
    )

    logger.info(
        "Report Generation Workflow Completed for Filing Month: %s",
        filing_month.name,
    )
