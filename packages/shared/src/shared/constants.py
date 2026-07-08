from enum import Enum


class CommonReportType(Enum):
    PURCHASE = "purchase"
    SALES = "sales"
    LAKH_TRANSACTIONS = "lakh_transactions"

    @property
    def file_extension(self) -> str:
        """Returns the appropriate file extension for the report type."""
        if self in (CommonReportType.PURCHASE, CommonReportType.SALES):
            return ".xlsx"
        if self == CommonReportType.LAKH_TRANSACTIONS:
            return ".xls"
        # Fallback for unexpected types or if a default is desired
        return ".bin"


# If need a tuple of all common report types (e.g., for validation)
ALL_COMMON_REPORT_TYPES = tuple(e.value for e in CommonReportType)


# Transaction Types (Integer Identifiers for DB Filtering/Internal Use)
class TransactionType(Enum):
    """Numeric identifiers for general transaction types, often used for database filtering or internal processing."""

    PURCHASE = 1
    SALES = 2

    @property
    def symbol(self) -> str:
        return {
            TransactionType.PURCHASE: "P",
            TransactionType.SALES: "S",
        }[self]


# New: Business Item Lists
FUEL_ITEMS: list[str] = ["petrol", "diesel"]

CANCELLED_STATUS = "001-03"
