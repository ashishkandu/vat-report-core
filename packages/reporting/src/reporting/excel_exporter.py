import logging
from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd
from openpyxl import load_workbook
from shared.constants import CommonReportType

from .models import ReportHeaderDetails

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


class ExcelExporter:
    """A class responsible for exporting various types of reports to Excel format."""

    def __init__(self):
        logger.info("ExcelExporter initialized.")

    def export_report_to_excel(
        self,
        report_type: CommonReportType,
        template_buffer: BytesIO,
        report_header_info: ReportHeaderDetails,
        transaction_df: pd.DataFrame,
        sheet_name: str,
    ) -> BytesIO:
        """
        Exports report data to an Excel file based on the report type and template.

        Args:
            report_type (CommonReportType): The type of report to export (e.g., PURCHASE, SALES).
            template_buffer (BytesIO): A BytesIO buffer containing the Excel template.
            report_header_info (ReportHeaderDetails): ReportHeaderDetails which contains header details
                                                  (e.g., 'PAN', 'office_name', 'year', 'month_name').
            transaction_df (pd.DataFrame): DataFrame containing the transaction data to append.
            sheet_name (str): The name of the sheet to write data to in the Excel file.

        Returns:
            BytesIO: A BytesIO buffer containing the completed Excel file.

        Raises:
            ValueError: If an unsupported report type is provided.
            Exception: For other errors during the export process.

        """
        logger.info("Starting Excel export for report type: %s", report_type.name)

        output_buffer = BytesIO()

        try:
            if report_type in [CommonReportType.PURCHASE, CommonReportType.SALES]:
                workbook = load_workbook(template_buffer)
                sheet: Worksheet = workbook.active

                detail = (
                    f"करदाता दर्ता नं (PAN) : {report_header_info.pan_no}        "
                    f"करदाताको नाम: {report_header_info.office_name}         "
                    f"साल: {report_header_info.year}    "
                    f"कर अवधि: {report_header_info.month_name}"
                )
                # --- Purchase/Sales Specific Logic ---
                logger.info("Applying Purchase/Sales template logic.")
                sheet["A4"] = detail

                # Save the workbook to an intermediate buffer to read its current state
                # (important for pandas to know existing rows)
                # intermediate_buffer = BytesIO()
                workbook.save(output_buffer)
                output_buffer.seek(0)

                # Read the intermediate buffer to determine the starting row for new data
                # Using engine='openpyxl' for compatibility with openpyxl
                reader = pd.read_excel(output_buffer, engine="openpyxl")
                start_row = (
                    len(reader) + 1
                )  # Append after the last row read by pandas (plus 1 for 0-indexing to actual row)

                # Append transaction data using ExcelWriter with overlay mode
                # The output_buffer is passed directly here for appending
                with pd.ExcelWriter(
                    output_buffer,
                    mode="a",
                    engine="openpyxl",
                    if_sheet_exists="overlay",
                ) as writer:
                    # Write the previously loaded workbook content to the writer first
                    # This is implicitly handled by `mode='a'` and `if_sheet_exists='overlay'`
                    # when using the *same* BytesIO buffer.
                    # pandas.ExcelWriter (openpyxl engine) will load the existing workbook
                    # from the buffer if mode='a' and if_sheet_exists='overlay' are used.
                    # So, we just need to write the new DataFrame.

                    transaction_df.to_excel(
                        writer,
                        index=False,
                        header=False,
                        sheet_name=sheet.title,  # Use the active sheet's name
                        startrow=start_row,
                    )
                output_buffer.seek(0)  # Reset buffer position after writing
                logger.info("Purchase/Sales template logic applied successfully.")

                workbook.close()

            elif report_type == CommonReportType.LAKH_TRANSACTIONS:
                # --- Lakh Transactions Specific Logic ---
                logger.info("Applying Lakh Transactions template logic.")

                try:
                    headers = pd.read_excel(template_buffer).columns
                except Exception:
                    logger.exception(
                        "Failed to read .xls template for Lakh Transactions",
                    )
                    raise

                transaction_df.columns = headers

                with pd.ExcelWriter(
                    output_buffer,
                    engine="openpyxl",  # Use openpyxl engine for .xlsx output
                ) as writer_df:
                    transaction_df.to_excel(
                        writer_df,
                        index=False,
                        header=True,
                        sheet_name=sheet_name,
                        startrow=0,  # Start writing from the very first row of the new .xlsx file
                    )
                output_buffer.seek(0)

                logger.info("Lakh Transactions template logic applied successfully.")

            else:
                msg = f"Unsupported report type for Excel export: '{report_type.name}'"
                logger.error(msg)
                raise ValueError(msg)  # noqa: TRY301

        except Exception:
            logger.exception(
                "Error during Excel report export for %s",
                report_type.name,
            )
            raise

        else:
            return output_buffer
