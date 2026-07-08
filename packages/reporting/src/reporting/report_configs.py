from dataclasses import dataclass
from enum import Enum

from shared.constants import CommonReportType


@dataclass
class ReportConfig:
    """
    Dataclass representing the configuration for a specific report.

    This holds all the non-logic-related metadata for a report.
    """

    name: CommonReportType
    sheet_name: str
    report_columns: list[str]  # The columns for the final DataFrame


class ReportConfigs(Enum):
    """
    Enumeration for different report configurations.

    This enum serves as a central registry for all report metadata.
    """

    PURCHASE = ReportConfig(
        name=CommonReportType.PURCHASE,
        sheet_name="Nepali PB",
        report_columns=[
            "Nepali Date",
            "Reference No",
            "__gap__",
            "Bill Receiveable Person",
            "Vat Pan No",
            "Grand Total",
            "__gap__",
            "Total_VATABLE_AMOUNT",
            "Total_VAT_AMOUNT",
        ],
    )
    SALES = ReportConfig(
        name=CommonReportType.SALES,
        sheet_name="Nepali SB",
        report_columns=[
            "Nepali Date",
            "Transaction ID",
            "Bill Receiveable Person",
            "Vat Pan No",
            "Grand Total",
            "__gap__",
            "Total_VATABLE_AMOUNT",
            "Total_VAT_AMOUNT",
        ],
    )
    LAKH_TRANSACTIONS = ReportConfig(
        name=CommonReportType.LAKH_TRANSACTIONS,
        sheet_name="Sheet1",
        report_columns=[
            "Vat Pan No",
            "Bill_Receiveable_Person",
            "Trade Name Type",
            "Transaction Type Symbol",
            "Cumulative_VATABLE_AMOUNT",
            "Exempted Amount",
        ],
    )

    @classmethod
    def get_config_by_name(cls, report_type: CommonReportType) -> ReportConfig:
        """Helper to get a ReportConfig by its enum value."""
        try:
            return next(item.value for item in cls if item.value.name == report_type)
        except StopIteration as exc:
            msg = f"Report config for '{report_type}' not found."
            raise ValueError(msg) from exc
