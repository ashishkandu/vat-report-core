"""Fiscal year reporting functionality."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Optional

import pandas as pd
from nepalidates import FilingMonth
from shared.constants import CommonReportType

from reporting.models import CompanyInfo
from reporting.processor import BaseReport, generate_summary_analytics

logger = logging.getLogger(__name__)


@dataclass
class FiscalYearRange:
    """Represents a fiscal year range for reporting."""

    start_month: FilingMonth
    end_month: FilingMonth

    @classmethod
    def from_fiscal_year(cls, fiscal_year: str) -> "FiscalYearRange":
        """Create a fiscal year range from a fiscal year string (e.g., '2080-81')."""
        try:
            start_year = int(fiscal_year.split("-")[0])
            start_month = FilingMonth.from_string(f"{start_year}-04")  # Shrawan
            end_month = FilingMonth.from_string(f"{start_year + 1}-03")  # Chaitra
            return cls(start_month=start_month, end_month=end_month)
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Invalid fiscal year format: {fiscal_year}. Expected format: YYYY-YY"
            ) from e

    @classmethod
    def from_date_range(cls, start: str, end: str) -> "FiscalYearRange":
        """Create a fiscal year range from start and end month strings (YYYY-MM)."""
        try:
            start_month = FilingMonth.from_string(start)
            end_month = FilingMonth.from_string(end)
            if end_month < start_month:
                raise ValueError("End month cannot be before start month")
            return cls(start_month=start_month, end_month=end_month)
        except ValueError as e:
            raise ValueError(
                f"Invalid date range: {start} to {end}. Expected format: YYYY-MM"
            ) from e


class FiscalYearReport(BaseReport):
    """Base class for fiscal year consolidated reports."""

    def __init__(
        self,
        fiscal_range: FiscalYearRange,
        company_info: CompanyInfo,
        report_type: CommonReportType,
    ):
        self.fiscal_range = fiscal_range
        self.company_info = company_info
        self.report_type = report_type
        self.monthly_dataframes: Dict[str, pd.DataFrame] = {}
        self.consolidated_dataframe: Optional[pd.DataFrame] = None

    def add_monthly_data(self, month: FilingMonth, df: pd.DataFrame) -> None:
        """Add monthly data to be consolidated."""
        self.monthly_dataframes[month.name] = df

    def consolidate_data(self) -> pd.DataFrame:
        """Combine all monthly data with period tracking."""
        if not self.monthly_dataframes:
            raise ValueError("No monthly data has been added")

        # Combine all monthly dataframes with period information
        consolidated = pd.concat(
            self.monthly_dataframes,
            keys=self.monthly_dataframes.keys(),
            names=["reporting_period", "index"],
        )
        consolidated = consolidated.reset_index(level="reporting_period")

        # Store consolidated data
        self.consolidated_dataframe = consolidated
        return consolidated

    def generate_summary(self) -> dict:
        """Generate consolidated metrics across all months."""
        if self.consolidated_dataframe is None:
            raise ValueError("Must call consolidate_data() before generating summary")

        # Generate overall summary
        overall_summary = generate_summary_analytics(self.consolidated_dataframe)

        # Generate per-month summaries
        monthly_summaries = {}
        for month, df in self.monthly_dataframes.items():
            monthly_summaries[month] = generate_summary_analytics(df)

        return {"overall": overall_summary, "monthly": monthly_summaries}

    def export_to_excel(self, template_buffer: BytesIO) -> BytesIO:
        """Export consolidated data to Excel with summary sheets."""
        if self.consolidated_dataframe is None:
            raise ValueError("Must call consolidate_data() before exporting")

        # TODO: Implement excel export with:
        # - Summary sheet showing consolidated totals
        # - Monthly breakdown sheets
        # - Period-over-period comparisons
        # - Charts and visualizations
        raise NotImplementedError(
            "Excel export for fiscal year reports not yet implemented"
        )


def process_fiscal_year_reports(
    fiscal_range: FiscalYearRange,
    company_info: CompanyInfo,
    raw_data_by_month: Dict[str, pd.DataFrame],
    downloaded_templates: Dict[CommonReportType, BytesIO],
) -> Dict[CommonReportType, BytesIO]:
    """
    Process and generate consolidated reports for a fiscal year or date range.

    Args:
        fiscal_range: The fiscal year or date range to process
        company_info: Company information for the reports
        raw_data_by_month: Dictionary mapping month names to raw transaction data
        downloaded_templates: Dictionary of Excel templates for each report type

    Returns:
        Dictionary mapping report types to Excel file buffers
    """
    exported_reports = {}

    for report_type in CommonReportType:
        if report_type not in downloaded_templates:
            logger.warning(f"No template found for {report_type.name}, skipping")
            continue

        report = FiscalYearReport(
            fiscal_range=fiscal_range,
            company_info=company_info,
            report_type=report_type,
        )

        # Add data from each month
        for month_name, raw_data in raw_data_by_month.items():
            month = FilingMonth.from_string(month_name)
            report.add_monthly_data(month, raw_data)

        # Consolidate and export
        report.consolidate_data()
        exported_reports[report_type] = report.export_to_excel(
            downloaded_templates[report_type]
        )

    return exported_reports
