from __future__ import annotations

from typing import Any

import pandas as pd

# --- Constants for Summary Data Keys ---
SUMMARY_KEYS = {
    "TOTAL_GRAND_PURCHASE_AMOUNT": "Total Grand Purchase Amount",
    "TOTAL_GRAND_SALES_AMOUNT": "Total Grand Sales Amount",
    "NET_VAT_PAYABLE_REFUNDABLE": "Net VAT Payable/Refundable",
    "TOTAL_SALES_TAXABLE_AMOUNT": "Total Sales Taxable Amount",
    "TOTAL_SALES_TAX_AMOUNT": "Total Sales Tax Amount",
    "TOTAL_PURCHASE_TAXABLE_AMOUNT": "Total Purchase Taxable Amount",
    "TOTAL_PURCHASE_TAX_AMOUNT": "Total Purchase Tax Amount",
    "TOTAL_SALES_ROUND_OFF": "Total Sales Round Off",
    "TOTAL_PURCHASE_ROUND_OFF": "Total Purchase Round Off",
    "PETROL_SALES_QUANTITY": "Petrol Sales Quantity",
    "DIESEL_SALES_QUANTITY": "Diesel Sales Quantity",
    "OTHER_FUEL_SALES_QUANTITY": "Other Fuel Sales Quantity",
    "OTHER_GOODS_SALES_QUANTITY": "Other Goods Sales Quantity",
    "PETROL_PURCHASE_QUANTITY": "Petrol Purchase Quantity",
    "DIESEL_PURCHASE_QUANTITY": "Diesel Purchase Quantity",
    "OTHER_FUEL_PURCHASE_QUANTITY": "Other Fuel Purchase Quantity",
    "OTHER_GOODS_PURCHASE_QUANTITY": "Other Goods Purchase Quantity",
    "TOP_5_SALES_TRANSACTIONS": "Top 5 Sales Transactions",
    "TOP_5_PURCHASE_TRANSACTIONS": "Top 5 Purchase Transactions",
    "TOP_5_SALES_CUSTOMERS": "Top 5 Sales Customers",
    "TOP_5_PURCHASE_SUPPLIERS": "Top 5 Purchase Suppliers",
    "TOP_5_SALES_ITEMS": "Top 5 Sales Items",
    "TOP_5_PURCHASE_ITEMS": "Top 5 Purchase Items",
    "TOTAL_CANCELLED_TRANSACTIONS": "Total Cancelled Transactions",
    "CANCELLED_TRANSACTIONS_LIST": "Cancelled Transactions List",
    "PURCHASE_TRANSACTIONS_COUNT": "Purchase Transactions Count",
    "SALES_TRANSACTIONS_COUNT": "Sales Transactions Count",
}


def format_npr_currency(
    amount: float | None,
    *,
    use_unicode_symbol: bool = True,
) -> str:
    """
    Formats a numeric amount into Nepali Rupee currency format.

    Uses the 3,2,2,... comma grouping system.

    Args:
        amount (float | int | None): Numeric amount to be formatted. If None, returns 'रु 0.00' or 'NPR 0.00'.
        use_unicode_symbol (bool): If True, uses 'रु'. If False, uses 'NPR ' as a fallback.

    Returns:
        str: The formatted currency string.

    Example:
        format_npr_currency(1234567.89) -> 'रु 12,34,567.89'
        format_npr_currency(1234567.89, use_unicode_symbol=False) -> 'NPR 12,34,567.89'

    """
    currency_symbol = "रु " if use_unicode_symbol else "NPR "

    if amount is None:
        amount = 0.0

    # Handle negative sign
    sign = "-" if amount < 0 else ""
    amount = abs(amount)  # Work with absolute value for formatting

    # Format the amount to ensure two decimal places
    formatted_amount = f"{amount:.2f}"

    # Split the amount into integer and fractional parts
    integer_part, fractional_part = formatted_amount.split(".")

    # Apply Nepali comma grouping for the integer part
    formatted_integer = _format_nepali_comma_grouping(integer_part)

    return f"{currency_symbol}{sign}{formatted_integer}.{fractional_part}"


def _format_nepali_comma_grouping(integer_part: str) -> str:
    """
    Helper function to apply Nepali comma grouping for the integer part.

    Args:
        integer_part (str): The integer part of the amount to be formatted.

    Returns:
        str: The formatted integer part with Nepali comma grouping.

    """
    if len(integer_part) <= 3:  # noqa: PLR2004
        return integer_part

    # Last three digits remain as is
    last_three = integer_part[-3:]
    remaining = integer_part[:-3]

    # Split remaining digits into chunks of 2
    chunks = []
    while remaining:
        if len(remaining) > 2:  # noqa: PLR2004
            chunks.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        else:
            chunks.insert(0, remaining)
            remaining = ""

    # Join chunks with commas and append the last three digits
    return ",".join(chunks) + "," + last_three


def _format_date(date_str: Any) -> str:
    """Formats a date string into YYYY-MM-DD. Handles None or invalid dates gracefully."""
    try:
        if date_str:
            # Ensure it's a datetime object before formatting
            return pd.to_datetime(date_str).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return "N/A"


def _get_summary_value(summary_data: dict[str, Any], key: str, default: Any = 0) -> Any:
    """Safely retrieves a value from summary_data using defined constants."""
    return summary_data.get(key, default)


class BaseReportFormatter:
    """Abstract base class for report formatters."""

    def __init__(self, summary_data: dict[str, Any], filing_month_name: str) -> None:
        self.summary_data = summary_data
        self.filing_month_name = filing_month_name

    def format_report(self) -> str:
        """
        Abstract method to be implemented by concrete formatters.

        Generates the formatted report string.
        """
        raise NotImplementedError
