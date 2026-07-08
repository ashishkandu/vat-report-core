from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Import necessary modules from other packages
from drive.auth import get_oauth_drive_service
from drive.client import GDriveClient
from drive.settings import GoogleDriveSettings
from shared import SharedSettings
from shared.constants import CommonReportType
from shared.logger import LoggerFactory

if TYPE_CHECKING:
    from io import BytesIO

    from nepalidates import FilingMonth
    from reporting.models import CompanyInfo

logger = LoggerFactory.get_logger(__name__)


def upload_reports_to_gdrive(
    exported_excel_reports: dict[Any, BytesIO],
    analytics_html_buffer: BytesIO | None,
    analytics_html_filename: str | None,
    filing_month: FilingMonth,
    company_info: CompanyInfo,
) -> None:
    """
    Uploads generated reports (Excel, HTML analytics) to Google Drive using OAuth credentials.

    The files are uploaded to a hierarchical folder structure:
    `[gdrive_reports_base_folder_name]/[Fiscal Year (e.g., 2081/82)]/[Month Name (e.g., Jestha)]`

    Args:
        exported_excel_reports (dict[Any, BytesIO]): A dictionary where keys are report types
            (e.g., CommonReportType) and values are BytesIO buffers of the Excel reports.
        analytics_html_buffer (BytesIO | None): The BytesIO buffer of the generated HTML analytics report.
        analytics_html_filename (str | None): The filename for the HTML analytics report (e.g., "summary_analytics_Baishakh.html").
        filing_month (FilingMonth): The FilingMonth object representing the period for these reports.
        company_info (CompanyInfo): The CompanyInfo DTO, useful for naming conventions.

    """
    settings = SharedSettings()  # Access settings here

    drive_settings = GoogleDriveSettings()

    # Check if there's anything to upload
    if not exported_excel_reports and (
        not analytics_html_buffer or not analytics_html_filename
    ):
        logger.info(
            "No reports or analytics HTML to upload to Google Drive. Skipping upload.",
        )
        return

    logger.info("--- Starting Google Drive Upload ---")
    try:
        # Authenticate using OAuth per-account token (configured in settings)
        # Safely access account settings with fallback to None
        upload_account = getattr(
            drive_settings, "UPLOAD_OAUTH_ACCOUNT", None
        ) or getattr(drive_settings, "DEFAULT_OAUTH_ACCOUNT", None)
        service = get_oauth_drive_service(account=upload_account)
        drive_client = GDriveClient(service)

        # Get or create base 'VAT Reports' folder (e.g., "VAT Reports")
        # Prioritize ID from settings if available to avoid lookup/creation.
        base_folder_id = settings.GDRIVE_REPORTS_BASE_FOLDER_ID
        if not base_folder_id:
            logger.info(
                "Google Drive base folder ID not configured. Discovering/creating by name: '%s'",
                settings.GDRIVE_REPORTS_BASE_FOLDER_NAME,
            )
            base_folder_id = drive_client.get_or_create_folder(
                settings.GDRIVE_REPORTS_BASE_FOLDER_NAME,
            )

        if not base_folder_id:
            logger.error(
                "Could not determine/create base Google Drive folder. Skipping upload.",
            )
            return

        # Use company_info for specific sub-folders if desired, e.g., company_info.pan_no
        # For simplicity, let's keep it fiscal year -> month for now.
        company_folder_name = (
            f"{company_info.pan_no} - {company_info.office_name}"
            if company_info
            else "General"
        )
        company_folder_id = drive_client.get_or_create_folder(
            company_folder_name,
            base_folder_id,
        )

        if not company_folder_id:
            logger.error(
                "Could not determine/create company folder '%s'. Skipping upload.",
                company_folder_name,
            )
            return

        fiscal_year_folder_name = filing_month.fiscal_year.replace(
            "/",
            "-",
        )  # Use a file-system friendly name
        fiscal_year_folder_id = drive_client.get_or_create_folder(
            fiscal_year_folder_name,
            company_folder_id,  # Parent is company folder
        )

        if not fiscal_year_folder_id:
            logger.error(
                "Could not determine/create fiscal year folder '%s'. Skipping upload.",
                fiscal_year_folder_name,
            )
            return

        month_folder_name = filing_month.name
        month_folder_id = drive_client.get_or_create_folder(
            month_folder_name,
            fiscal_year_folder_id,
        )

        if not month_folder_id:
            logger.error(
                "Could not determine/create month folder '%s'. Skipping upload.",
                month_folder_name,
            )
            return

        # Upload Excel reports
        for report_type, file_buffer in exported_excel_reports.items():
            try:
                file_buffer.seek(0)  # Ensure buffer is at the start for re-reading

                # Derive filename and MIME type from CommonReportType
                file_name = f"{report_type.name} - {filing_month.name}{report_type.file_extension}"
                mime_type = {
                    CommonReportType.PURCHASE: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    CommonReportType.SALES: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    CommonReportType.LAKH_TRANSACTIONS: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }.get(report_type, "application/octet-stream")

                uploaded_file_meta = drive_client.upload_file(
                    file_name=file_name,
                    file_buffer=file_buffer,
                    mime_type=mime_type,
                    parent_folder_id=month_folder_id,
                )
                logger.info(
                    "Uploaded report: '%s' (Drive ID: %s)",
                    uploaded_file_meta.name,
                    uploaded_file_meta.id,
                )
            except Exception:
                logger.exception(
                    "Failed to upload report type '%s' to Google Drive.",
                    report_type.name,
                )

        # Upload Analytics HTML
        if analytics_html_buffer and analytics_html_filename:
            try:
                analytics_html_buffer.seek(0)
                uploaded_html_meta = drive_client.upload_file(
                    file_name=analytics_html_filename,
                    file_buffer=analytics_html_buffer,
                    mime_type="text/html",
                    parent_folder_id=month_folder_id,
                )
                logger.info(
                    "Uploaded analytics HTML: '%s' (Drive ID: %s)",
                    uploaded_html_meta.name,
                    uploaded_html_meta.id,
                )
            except Exception:
                logger.exception(
                    "Failed to upload analytics HTML '%s' to Google Drive.",
                    analytics_html_filename,
                )

    except Exception as e:
        logger.exception("An error occurred during Google Drive upload process.")
        msg = f"Google Drive upload failed: {e}"
        raise RuntimeError(msg) from e

    logger.info("Google Drive upload completed.")
