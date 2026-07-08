from nepalidates.filing_month import FilingMonth
from shared.logger import LoggerFactory

from .workflow import execute_vat_workflow


def main() -> None:
    LoggerFactory.configure_logging(debug_mode=False)
    execute_vat_workflow(
        FilingMonth.previous(),
        save_analytics_html_locally=False,
        send_email=True,
        upload_to_gdrive=False,
    )
