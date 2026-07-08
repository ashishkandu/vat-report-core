from pyBSDate import bsdate

from .date_utils import convert_bs_to_ad, get_nepali_month_name
from .filing_month import FilingMonth


def run() -> None:
    filing_m = FilingMonth(2082, 1)
    print(f"Filing Month Name: {filing_m.name}")
    print(f"BS Date Range: {filing_m.bs_date_range}")
    print(f"AD Date Range: {filing_m.ad_date_range}")
    print(f"Fiscal Year: {filing_m.fiscal_year}")

    print(f"\nPrevious month and year for 2082/1: {get_nepali_month_name(12)}")
    print(f"Converted BS to AD: {convert_bs_to_ad(bsdate(2080, 10, 15))}")

    print("Current Filing Month", FilingMonth.current())
    print("Previous Filing Month", FilingMonth.previous())
