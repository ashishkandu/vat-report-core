from __future__ import annotations

from typing import Any

from .base import (
    SUMMARY_KEYS,
    BaseReportFormatter,
    _format_date,
    _get_summary_value,
    format_npr_currency,
)


class ConsoleReportFormatter(BaseReportFormatter):
    """Formats the summary analytics dictionary into a human-readable plain text string for console output."""

    def _add_header(self, console_parts: list[str]) -> None:
        """Adds the main console header and introduction."""
        console_parts.append(f"VAT Report Analytics for {self.filing_month_name}\n")
        console_parts.append(
            "Here is a summary of your key VAT-related analytics for the selected period.\n",
        )

    def _add_financial_summary(self, console_parts: list[str]) -> None:
        """Adds the overall financial summary section (KPIs) for console."""
        console_parts.append("\n=== Overall Financial Summary ===\n")

        total_purchase = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["TOTAL_GRAND_PURCHASE_AMOUNT"],
        )
        total_sales = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["TOTAL_GRAND_SALES_AMOUNT"],
        )
        net_vat = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["NET_VAT_PAYABLE_REFUNDABLE"],
        )

        sales_count = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["SALES_TRANSACTIONS_COUNT"],
            0,
        )
        purchase_count = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["PURCHASE_TRANSACTIONS_COUNT"],
            0,
        )

        vat_label = "Net VAT Payable" if net_vat >= 0 else "Net VAT Refundable"
        console_parts.append(
            f"{vat_label}: {format_npr_currency(net_vat, use_unicode_symbol=False)}\n",
        )

        console_parts.append(
            f"Total Sales Taxable Amount: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_SALES_TAXABLE_AMOUNT']), use_unicode_symbol=False)}",
        )
        console_parts.append(
            f"Total Sales Tax Amount: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_SALES_TAX_AMOUNT']), use_unicode_symbol=False)}\n",
        )
        console_parts.append(
            f"Total Purchase Taxable Amount: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_PURCHASE_TAXABLE_AMOUNT']), use_unicode_symbol=False)}",
        )
        console_parts.append(
            f"Total Purchase Tax Amount: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_PURCHASE_TAX_AMOUNT']), use_unicode_symbol=False)}\n",
        )

        console_parts.append(
            f"Total Grand Sales Amount: {format_npr_currency(total_sales, use_unicode_symbol=False)}",
        )
        console_parts.append(
            f"Total Grand Purchase Amount: {format_npr_currency(total_purchase, use_unicode_symbol=False)}\n",
        )

        console_parts.append(
            f"Total Sales Round Off: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_SALES_ROUND_OFF']), use_unicode_symbol=False)}",
        )
        console_parts.append(
            f"Total Purchase Round Off: {format_npr_currency(_get_summary_value(self.summary_data, SUMMARY_KEYS['TOTAL_PURCHASE_ROUND_OFF']), use_unicode_symbol=False)}\n",
        )

        console_parts.append(f"Sales Transactions Count: {sales_count:,}")
        console_parts.append(f"Purchase Transactions Count: {purchase_count:,}\n")

    def _add_fuel_quantities(self, console_parts: list[str]) -> None:
        """Adds the fuel and goods quantities section for console."""
        console_parts.append("\n=== Fuel and Goods Quantities (Litres/Units) ===\n")

        console_parts.append("Sales:\n")
        console_parts.append(
            f"- Petrol Sales Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['PETROL_SALES_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Diesel Sales Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['DIESEL_SALES_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Other Fuel Sales Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['OTHER_FUEL_SALES_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Other Goods Sales Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['OTHER_GOODS_SALES_QUANTITY']):,.2f}\n",
        )

        console_parts.append("Purchases:\n")
        console_parts.append(
            f"- Petrol Purchase Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['PETROL_PURCHASE_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Diesel Purchase Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['DIESEL_PURCHASE_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Other Fuel Purchase Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['OTHER_FUEL_PURCHASE_QUANTITY']):,.2f}",
        )
        console_parts.append(
            f"- Other Goods Purchase Quantity: {_get_summary_value(self.summary_data, SUMMARY_KEYS['OTHER_GOODS_PURCHASE_QUANTITY']):,.2f}\n",
        )

    def _create_transaction_table(
        self,
        title: str,
        transactions: list[dict[str, Any]],
    ) -> str:
        """Generates a plain text table for transactions for console output."""
        table_lines = []
        if not transactions:
            return f"--- {title} ---\nNo data available.\n"

        headers = [
            "Bill Date",
            "Transaction ID",
            "Party",
            "Grand Total",
        ]

        # Calculate max width for each column
        col_widths = {header: len(header) for header in headers}
        for tx in transactions:
            col_widths["Bill Date"] = max(
                col_widths["Bill Date"],
                len(_format_date(tx.get("Bill Date"))),
            )
            col_widths["Transaction ID"] = max(
                col_widths["Transaction ID"],
                len(str(tx.get("Transaction ID", "N/A"))),
            )
            col_widths["Party"] = max(
                col_widths["Party"],
                len(str(tx.get("Bill Receiveable Person", "N/A"))),
            )
            col_widths["Grand Total"] = max(
                col_widths["Grand Total"],
                len(
                    format_npr_currency(
                        tx.get("Grand Total", 0),
                        use_unicode_symbol=False,
                    ),
                ),
            )

        header_line = " | ".join(
            [header.ljust(col_widths[header]) for header in headers],
        )
        table_lines.append(header_line)
        table_lines.append("-" * len(header_line))

        for tx in transactions:
            row_data = [
                _format_date(tx.get("Bill Date")).ljust(col_widths["Bill Date"]),
                str(tx.get("Transaction ID", "N/A")).ljust(
                    col_widths["Transaction ID"],
                ),
                str(tx.get("Bill Receiveable Person", "N/A")).ljust(
                    col_widths["Party"],
                ),
                format_npr_currency(
                    tx.get("Grand Total", 0),
                    use_unicode_symbol=False,
                ).ljust(col_widths["Grand Total"]),
            ]
            table_lines.append(" | ".join(row_data))

        return f"--- {title} ---\n" + "\n".join(table_lines) + "\n"

    def _add_top_transactions(self, console_parts: list[str]) -> None:
        """Adds the top transactions section for console."""
        console_parts.append("\n=== Top Transactions ===\n")
        console_parts.append(
            self._create_transaction_table(
                "Top 5 Sales Transactions",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_TRANSACTIONS"],
                    [],
                ),
            ),
        )
        console_parts.append(
            self._create_transaction_table(
                "Top 5 Purchase Transactions",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_TRANSACTIONS"],
                    [],
                ),
            ),
        )

    def _create_top_list(self, title: str, data: dict[str, Any]) -> str:
        """Generates a plain text list for top customers/suppliers/items for console output."""
        if not data:
            return f"--- {title} ---\nNo data available.\n"

        list_lines = [f"--- {title} ---"]
        for name, value in data.items():
            if isinstance(value, int | float):
                list_lines.append(
                    f"- {name}: {format_npr_currency(value, use_unicode_symbol=False)}",
                )
            else:
                list_lines.append(f"- {name}: {value}")
        return "\n".join(list_lines) + "\n"

    def _add_top_entities(self, console_parts: list[str]) -> None:
        """Adds the top customers, suppliers, and items section for console."""
        console_parts.append("\n=== Top Customers, Suppliers, and Items ===\n")
        console_parts.append(
            self._create_top_list(
                "Top 5 Sales Customers",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_CUSTOMERS"],
                    {},
                ),
            ),
        )
        console_parts.append(
            self._create_top_list(
                "Top 5 Purchase Suppliers",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_SUPPLIERS"],
                    {},
                ),
            ),
        )
        console_parts.append(
            self._create_top_list(
                "Top 5 Sales Items",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_ITEMS"],
                    {},
                ),
            ),
        )
        console_parts.append(
            self._create_top_list(
                "Top 5 Purchase Items",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_ITEMS"],
                    {},
                ),
            ),
        )

    def _add_cancelled_transactions(self, console_parts: list[str]) -> None:
        """Adds the cancelled transactions summary and details for console."""
        console_parts.append("\n=== Cancelled Transactions Summary ===\n")
        cancelled_tx_list = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["CANCELLED_TRANSACTIONS_LIST"],
            [],
        )

        if cancelled_tx_list:
            total_cancelled = _get_summary_value(
                self.summary_data,
                SUMMARY_KEYS["TOTAL_CANCELLED_TRANSACTIONS"],
            )
            console_parts.append(f"Total Cancelled Transactions: {total_cancelled}\n")

            table_lines = ["--- Cancelled Transactions Details: ---"]
            headers = [
                "Date",
                "Transaction ID",
                "Party",
                "Type",
                "Grand Total",
                "Reason",
            ]

            # Calculate max width for each column
            col_widths = {header: len(header) for header in headers}
            for tx in cancelled_tx_list:
                col_widths["Date"] = max(
                    col_widths["Date"],
                    len(_format_date(tx.get("Cancellation_Date"))),
                )
                col_widths["Transaction ID"] = max(
                    col_widths["Transaction ID"],
                    len(str(tx.get("Transaction ID", "N/A"))),
                )
                col_widths["Party"] = max(
                    col_widths["Party"],
                    len(str(tx.get("Bill_Receiveable_Person", "N/A"))),
                )
                col_widths["Type"] = max(
                    col_widths["Type"],
                    len(str(tx.get("Transaction_Type_Symbol", "N/A"))),
                )
                col_widths["Grand Total"] = max(
                    col_widths["Grand Total"],
                    len(
                        format_npr_currency(
                            tx.get("Transaction_Grand_Total", 0),
                            use_unicode_symbol=False,
                        ),
                    ),
                )
                col_widths["Reason"] = max(
                    col_widths["Reason"],
                    len(str(tx.get("Why_Update", "N/A"))),
                )

            # Header Row
            header_line = " | ".join(
                [header.ljust(col_widths[header]) for header in headers],
            )
            table_lines.append(header_line)
            table_lines.append("-" * len(header_line))  # Separator

            # Data Rows
            for tx in cancelled_tx_list:
                row_data = [
                    _format_date(tx.get("Cancellation_Date")).ljust(col_widths["Date"]),
                    str(tx.get("Transaction ID", "N/A")).ljust(
                        col_widths["Transaction ID"],
                    ),
                    str(tx.get("Bill_Receiveable_Person", "N/A")).ljust(
                        col_widths["Party"],
                    ),
                    str(tx.get("Transaction_Type_Symbol", "N/A")).ljust(
                        col_widths["Type"],
                    ),
                    format_npr_currency(
                        tx.get("Transaction_Grand_Total", 0),
                        use_unicode_symbol=False,
                    ).ljust(col_widths["Grand Total"]),
                    str(tx.get("Why_Update", "N/A")).ljust(col_widths["Reason"]),
                ]
                table_lines.append(" | ".join(row_data))
            console_parts.append("\n".join(table_lines) + "\n")
        else:
            console_parts.append("No cancelled transactions for this period.\n")

    def format_report(self) -> str:
        """Generates the plain text console report string."""
        console_parts = []

        self._add_header(console_parts)
        self._add_financial_summary(console_parts)
        self._add_fuel_quantities(console_parts)
        self._add_top_transactions(console_parts)
        self._add_top_entities(console_parts)
        self._add_cancelled_transactions(console_parts)

        return "\n".join(console_parts)
