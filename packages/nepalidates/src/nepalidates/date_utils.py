from dataclasses import dataclass
from datetime import date

import nepali_datetime
from pyBSDate import bsdate

LAST_MONTH = 12


def get_nepali_month_name(month: int) -> str:
    """Returns Nepali month name for a given month number (1-12)."""
    if not (1 <= month <= LAST_MONTH):
        msg = "Month must be in 1..12"
        raise ValueError(msg)
    return nepali_datetime._FULLMONTHNAMES[month]  # noqa: SLF001


def get_previous_month_and_year(
    current_month: int,
    current_year: int,
) -> tuple[int, int]:
    """Returns (previous_month, previous_year) for a given month/year."""
    if current_month == 1:
        return 12, current_year - 1
    return current_month - 1, current_year


def get_next_month_and_year(
    current_month: int,
    current_year: int,
) -> tuple[int, int]:
    """Returns (next_month, next_year) for a given month/year."""
    if current_month == LAST_MONTH:
        return 1, current_year + 1
    return current_month + 1, current_year


def convert_bs_to_ad(bs_date: bsdate) -> date:
    """Converts BS date to AD date."""
    return bs_date.addate


@dataclass(frozen=True)
class BSDateRange:
    """Represents a date range in Bikram Sambat (BS) format."""

    start: bsdate
    end: bsdate

    def __str__(self) -> str:
        return f"{self.start} - {self.end}"


@dataclass(frozen=True)
class ADDateRange:
    """Represents a date range in Anno Domini (AD) format."""

    start: date
    end: date

    def __str__(self) -> str:
        return f"{self.start} - {self.end}"
