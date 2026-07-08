from __future__ import annotations

import functools
from datetime import date as ad_date
from typing import ClassVar

import nepali_datetime
from pyBSDate import bsdate

from .date_utils import (
    ADDateRange,
    BSDateRange,
    convert_bs_to_ad,
    get_nepali_month_name,
)


class FilingMonth:
    """Represents a Nepali Filing Month for VAT and other reporting purposes."""

    FISCAL_YEAR_START_MONTH: ClassVar[int] = 4

    MAX_NEPALI_MONTH: ClassVar[int] = 12

    MIN_NEPALI_YEAR_FOR_SELECTION: ClassVar[int] = 2078

    # Instance Attributes (Type Hinting for clarity)
    year: int
    month: int
    _name: str
    _bs_date_range: BSDateRange | None = None  # Initialize to None for explicit caching
    _ad_date_range: ADDateRange | None = None
    _fiscal_year: str | None = None

    def __init__(self, year: int, month: int):
        # 1. Type and Value Validation (Early exit for invalid inputs)
        if not all(isinstance(arg, int) for arg in [year, month]):
            msg = "Year and month must be integers."
            raise TypeError(msg)
        if not (1 <= month <= self.MAX_NEPALI_MONTH):
            msg = f"Month must be between 1 and {self.MAX_NEPALI_MONTH}."
            raise ValueError(msg)

        current_bs_date = nepali_datetime.date.today()

        # 2. Future Month Validation (Ensures we don't create FilingMonth objects for future periods)
        if year > current_bs_date.year:
            msg = f"Year must not be in the future (current BS year: {current_bs_date.year})."
            raise ValueError(
                msg,
            )
        if year == current_bs_date.year and month > current_bs_date.month:
            msg = (
                f"Month must not be in the future (current BS month: {current_bs_date.month}) "
                f"for the current year {current_bs_date.year}."
            )
            raise ValueError(
                msg,
            )

        # 3. Minimum Historical Year Validation
        if year < self.MIN_NEPALI_YEAR_FOR_SELECTION:
            msg = f"Year must be >= {self.MIN_NEPALI_YEAR_FOR_SELECTION} for historical data."
            raise ValueError(
                msg,
            )

        self.year = year
        self.month = month
        self._name = get_nepali_month_name(month)

    @property
    @functools.cache  # noqa: B019
    def bs_date_range(self) -> BSDateRange:
        """Returns the BS date range for the filing month."""
        last_day = nepali_datetime._days_in_month(year=self.year, month=self.month)  # noqa: SLF001
        return BSDateRange(
            bsdate(year=self.year, month=self.month, day=1),
            bsdate(year=self.year, month=self.month, day=last_day),
        )

    @property
    @functools.cache  # noqa: B019
    def ad_date_range(self) -> ADDateRange:
        """Returns the AD date range corresponding to the BS filing month."""
        bs_range = self.bs_date_range
        return ADDateRange(
            convert_bs_to_ad(bs_range.start),
            convert_bs_to_ad(bs_range.end),
        )

    @property
    def name(self) -> str:
        """Returns the Nepali name of the month (e.g., 'Bhadra')."""
        return self._name

    @property
    @functools.cache  # noqa: B019
    def fiscal_year(self) -> str:
        """
        Calculates and returns the fiscal year in 'YYYY/YY' format (e.g., '2080/81').

        Based on `FISCAL_YEAR_START_MONTH`.
        """
        if self.month >= self.FISCAL_YEAR_START_MONTH:
            return f"{self.year}/{str(self.year + 1)[2:]}"
        return f"{self.year - 1}/{str(self.year)[2:]}"

    # --- Comparison Methods ---
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FilingMonth):
            return NotImplemented
        return self.year == other.year and self.month == other.month

    def __hash__(self) -> int:
        """Makes FilingMonth objects hashable, essential for sets and dict keys."""
        return hash((self.year, self.month))

    def __lt__(self, other: FilingMonth) -> bool:
        return (self.year, self.month) < (other.year, other.month)

    def __gt__(self, other: FilingMonth) -> bool:
        return (self.year, self.month) > (other.year, other.month)

    def __le__(self, other: FilingMonth) -> bool:
        return (self.year, self.month) <= (other.year, other.month)

    def __ge__(self, other: FilingMonth) -> bool:
        return (self.year, self.month) >= (other.year, other.month)

    # --- String Representation ---
    def __repr__(self) -> str:
        return (
            f"FilingMonth(year={self.year}, month={self.month}, name='{self.name}', "
            f"fiscal_year='{self.fiscal_year}')"
        )

    def __str__(self) -> str:
        """Human-readable string for the filing month."""
        return f"{self.name} {self.year} BS (Fiscal Year {self.fiscal_year})"

    # --- Class Methods for Construction ---
    @classmethod
    def from_bsdate(cls, bs_date_obj: bsdate) -> FilingMonth:
        """Create FilingMonth from a `bsdate` object."""
        if not isinstance(bs_date_obj, bsdate):
            msg = "Input must be a 'bsdate' object."
            raise TypeError(msg)
        return cls(bs_date_obj.year, bs_date_obj.month)

    @classmethod
    def from_ad_date(cls, ad_date_obj: ad_date) -> FilingMonth:
        """Create FilingMonth from an AD date object."""
        if not isinstance(ad_date_obj, ad_date):
            msg = "Input must be a Python 'datetime.date' object."
            raise TypeError(msg)
        bs = bsdate.from_ad_date(ad_date_obj)
        return cls(bs.year, bs.month)

    @classmethod
    def current(cls) -> FilingMonth:
        """Return the FilingMonth for the current Nepali date."""
        today_bs = nepali_datetime.date.today()
        return cls(today_bs.year, today_bs.month)

    @classmethod
    def previous(cls) -> FilingMonth:
        """Return the FilingMonth for the immediately preceding Nepali month."""
        return FilingMonth.current().get_relative_month(-1)

    @classmethod
    def from_string(cls, filing_month_str: str) -> FilingMonth:
        """
        Creates a FilingMonth instance from a BSYYYY-MM string.

        e.g., "2081-01" for Baishakh 2081 BS.
        """
        try:
            year_bs, month_num = map(int, filing_month_str.split("-"))

            return FilingMonth(year=year_bs, month=month_num)
        except (ValueError, IndexError) as e:
            msg = f"Invalid filing month format: '{filing_month_str}'. Expected BSYYYY-MM (e.g., 2081-02)."
            raise ValueError(msg) from e

    # --- Instance Methods ---
    def get_relative_month(self, offset: int) -> FilingMonth:
        """
        Returns a FilingMonth object relative to the current month by a given offset.

        Args:
            offset (int): Number of months to offset. Positive for future, negative for past.

        Returns:
            FilingMonth: The calculated FilingMonth object.

        Raises:
            ValueError: If the calculated month is in the future relative to the current date,
                        or if it's earlier than `MIN_NEPALI_YEAR_FOR_SELECTION`.

        """
        if not isinstance(offset, int):
            msg = "Offset must be an integer."
            raise TypeError(msg)

        # Calculate target year and month
        total_months = (self.year * self.MAX_NEPALI_MONTH) + self.month + offset
        target_year = (total_months - 1) // self.MAX_NEPALI_MONTH
        target_month_num = (total_months - 1) % self.MAX_NEPALI_MONTH + 1

        # Use the FilingMonth constructor's built-in validation for future and min year checks
        return FilingMonth(target_year, target_month_num)

    def next(self) -> "FilingMonth":
        """
        Return the FilingMonth for the immediately following Nepali month.

        This is a convenience wrapper around `get_relative_month(1)` and keeps the
        API backwards-compatible for callers that expect a `.next()` method
        (for example, the fiscal-year workflow iterator).
        """
        return self.get_relative_month(1)

    # --- Static Methods ---
    @staticmethod
    def get_filing_month_range(
        num_previous: int = 12,
        min_year: int = MIN_NEPALI_YEAR_FOR_SELECTION,
    ) -> list[FilingMonth]:
        """
        Generates a sorted list of unique FilingMonth objects for selection.

        The range includes a specified number of previous months relative to the
        current month, ensuring all generated months are valid (not in the future,
        and not older than `min_year`).

        Args:
            num_previous (int): Number of previous months to include relative to the current month.
                                Defaults to 12.
            min_year (int): The absolute minimum BS year to include in the range.
                            Defaults to `FilingMonth.MIN_NEPALI_YEAR_FOR_SELECTION`.

        Returns:
            list[FilingMonth]: A sorted list of unique FilingMonth objects,
                                from oldest to newest.

        """
        if not isinstance(num_previous, int) or num_previous < 0:
            msg = "num_previous must be a non-negative integer."
            raise ValueError(msg)
        if not isinstance(min_year, int) or min_year < 1:
            msg = "min_year must be a positive integer."
            raise ValueError(msg)

        months_set: set[FilingMonth] = set()
        current_fm = FilingMonth.current()

        # Add current month
        months_set.add(current_fm)

        # Add previous months based on num_previous
        for i in range(1, num_previous + 1):
            try:
                fm = current_fm.get_relative_month(-i)
                # get_relative_month and FilingMonth constructor already handle min_year and future checks
                months_set.add(fm)
            except ValueError:
                # If get_relative_month raises ValueError (e.g., goes too far back), stop adding
                break

        # Convert to list, sort, and return
        sorted_months = sorted(months_set)
        return sorted_months
