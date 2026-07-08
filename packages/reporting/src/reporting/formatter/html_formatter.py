from __future__ import annotations

import datetime
from typing import Any

from premailer import transform

from .base import (
    SUMMARY_KEYS,
    BaseReportFormatter,
    _format_date,
    _get_summary_value,
    format_npr_currency,
)


class HtmlReportFormatter(BaseReportFormatter):
    """Formats the summary analytics dictionary into a human-readable HTML string for email, with CSS inlined for maximum compatibility."""

    HTML_STYLES = """
        <style>
            body {
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333333;
                background-color: #F8F9FA;
                font-size: 16px;
            }
            .container {
                max-width: 700px;
                margin: 20px auto; /* Centered with top/bottom margin */
                padding: 30px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); /* Softer, more prominent shadow */
                border-radius: 12px; /* More rounded corners */
                background-color: #ffffff; /* Pure white background for the main card */
                margin: 0 auto;
                padding: 0; /* Padding moves to individual section-box */
                background-color: transparent; /* Main container is transparent */
                box-shadow: none; /* No shadow on main container */
                border-radius: 0;
            }
            .section-box { /* New style for individual sections as cards */
                box-sizing: border-box;
                padding: 5px 16px; /* Internal padding for each section */
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px; /* Slight rounded corners */
                margin-bottom: 20px; /* Space between sections */
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); /* Very subtle shadow */
                overflow-x: auto;
            }
            h1 {
                text-align: center;
                color: #0056B3; /* Darker blue for main title */
                font-size: 28px;
                margin-bottom: 25px;
                padding-bottom: 10px;
                border-bottom: 2px solid #E9ECEF; /* Subtle border under main title */
            }
            h2 {
                font-size: 22px;
                color: #0056B3; /* Darker blue for section headers */
                /* margin-top: 30px; */
                margin-bottom: 15px;
                border-bottom: 1px solid #E9ECEF; /* Lighter border for sub-sections */
                padding-bottom: 8px;
            }
            h3 {
                color: #34495e; /* Slightly darker shade for sub-sub-headers */
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 18px;
            }
            p {
                margin-bottom: 10px;
            }
            ul {
                list-style-type: none;
                padding: 0;
                margin: 0 0 20px 0; /* Add bottom margin for spacing */
            }
            ul li {
                margin-bottom: 8px;
                line-height: 1.5;
                font-size: 16px;
            }
            ul li strong {
                color: #34495e; /* Stronger contrast for labels */
            }
            .kpi-row {
                display: block; /* Ensures block-level behavior even if inlined */
                margin-bottom: 8px;
                font-size: 1.1em;
                padding: 5px 0;
            }
            .kpi-label {
                font-weight: bold;
                color: #007BFF; /* Primary blue for KPI labels */
                display: inline-block; /* Keep label and value on same line */
                min-width: 220px; /* Align labels */
            }
            .kpi-value {
                font-weight: bold;
                display: inline-block;
            }

            /* KPI Highlight */
            .vat-highlight {
                background-color: #F0F8FF;
                border-left: 6px solid #007BFF;
                padding: 16px 24px;
                margin-bottom: 32px;
                border-radius: 10px;
            }
            .vat-highlight strong {
                font-size: 20px;
                color: #007BFF;
            }
            .vat-highlight .value {
                font-size: 24px;
                font-weight: bold;
                margin-left: 12px;
                color: #2C3E50;
            }
            .vat-highlight.positive {
                background-color: #FFF5F5;         /* Light red background */
                border-left: 6px solid #DC3545;    /* Red border */
            }
            .vat-highlight.positive strong {
                color: #DC3545;                    /* Red text */
            }

            .vat-highlight.negative {
                background-color: #F3FFF5;         /* Light green background */
                border-left: 6px solid #28A745;    /* Green border */
            }
            .vat-highlight.negative strong {
                color: #28A745;                    /* Green text */
            }

            .kpi-grid {
                text-align: center; /* Center the inline-block cards */
                font-size: 0; /* Fix spacing between inline-blocks */
                margin: 0 -1%;
            }

            .kpi-card {
                display: inline-block;
                vertical-align: top;
                width: 48%; /* Two cards per row */
                margin: 1%;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px 16px;
                text-align: left;
                font-size: 15px;
                box-sizing: border-box;
                height: auto;
            }

            .kpi-card strong {
                display: block;
                color: #007BFF;
                font-size: 14px;
                margin-bottom: 4px;
            }

            .kpi-card span {
                font-weight: bold;
                font-size: 16px;
                color: #2c3e50;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 1em;
                margin-bottom: 2em;
                font-size: 0.85em; /* Scales with body font size */
                table-layout: auto;
            }
            th, td {
                border: 1px solid #dee2e6;
                padding: 0.6em 0.5em;
                text-align: left;
                vertical-align: top;
                font-size: 0.85em;
                white-space: normal;
            }
            th {
                background-color: #E9ECEF; /* Light grey header background */
                color: #495057; /* Darker text for headers */
                font-weight: bold;
            }
            tr:nth-child(even) {
                background-color: #f6f6f6; /* Slightly off-white for even rows */
            }
            .footer {
                margin-top: 30px;
                text-align: center;
                font-size: 12px;
                color: #6C757D; /* Muted grey for footer text */
                border-top: 1px solid #E9ECEF;
                padding-top: 20px;
                line-height: 1.4;
            }
            .kpi-table {
                width: 100%;
                border-spacing: 12px 16px; /* spacing between 'cards' */
                border-collapse: separate;
            }
            .kpi-table td {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                color: #333333;
                vertical-align: top;
            }
            .kpi-table .label {
                color: #007BFF;
                font-weight: bold;
                font-size: 13px;
                margin-bottom: 4px;
                display: block;
            }
            .kpi-table .value {
                font-weight: bold;
                color: #2c3e50;
                font-size: 16px;
            }
        </style>
        """

    def _add_header(self, html_parts: list[str]) -> None:
        """Adds the main HTML header and introduction."""
        html_parts.append('<div class="container">')
        html_parts.append('<div class="section-box">')  # Main title section
        html_parts.append(f"<h1>VAT Analytics Report for {self.filing_month_name}</h1>")
        html_parts.append("<p>Dear Valued Client,</p>")
        html_parts.append(
            "<p>This report provides a comprehensive summary of your VAT-related financial activities for the selected period.</p>",
        )

    def _add_vat_highlight(self, html_parts: list[str]) -> None:
        net_vat = _get_summary_value(
            self.summary_data,
            SUMMARY_KEYS["NET_VAT_PAYABLE_REFUNDABLE"],
        )
        vat_label = "Net VAT Refundable" if net_vat < 0 else "Net VAT Payable"
        highlight_class = "negative" if net_vat < 0 else "positive"

        html_parts.append(f'<div class="vat-highlight {highlight_class}">')
        html_parts.append(
            f"<strong>{vat_label}:</strong><span class='value'>{format_npr_currency(net_vat)}</span>",
        )
        html_parts.append("</div>")  # Close vat-highlight
        html_parts.append("</div>")  # Close section-box

    def _add_financial_summary(self, html_parts: list[str]) -> None:
        """Adds the overall financial summary section (KPIs) using table-based cards (email-safe)."""
        html_parts.append('<div class="section-box">')
        html_parts.append("<h2>Overall Financial Summary</h2>")

        values = [
            (
                "Total Sales Taxable Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_SALES_TAXABLE_AMOUNT"],
                ),
            ),
            (
                "Total Sales Tax Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_SALES_TAX_AMOUNT"],
                ),
            ),
            (
                "Total Purchase Taxable Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_PURCHASE_TAXABLE_AMOUNT"],
                ),
            ),
            (
                "Total Purchase Tax Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_PURCHASE_TAX_AMOUNT"],
                ),
            ),
            (
                "Total Grand Sales Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_GRAND_SALES_AMOUNT"],
                ),
            ),
            (
                "Total Grand Purchase Amount",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_GRAND_PURCHASE_AMOUNT"],
                ),
            ),
            (
                "Total Sales Round Off",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_SALES_ROUND_OFF"],
                ),
            ),
            (
                "Total Purchase Round Off",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOTAL_PURCHASE_ROUND_OFF"],
                ),
            ),
            (
                "Sales Transactions Count",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["SALES_TRANSACTIONS_COUNT"],
                    0,
                ),
            ),
            (
                "Purchase Transactions Count",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["PURCHASE_TRANSACTIONS_COUNT"],
                    0,
                ),
            ),
        ]

        # Start table layout
        html_parts.append(
            '<table class="kpi-table" role="presentation" cellpadding="0" cellspacing="0">',
        )

        # Render as rows with 2 columns
        for i in range(0, len(values), 2):
            html_parts.append("<tr>")
            for j in range(2):
                if i + j < len(values):
                    label, amount = values[i + j]
                    # --- Show count as integer, others as currency ---
                    if "Count" in label:
                        html_parts.append(
                            f"<td width='50%'><span class='label'>{label}</span><span class='value'>{int(amount):,}</span></td>",
                        )
                    else:
                        html_parts.append(
                            f"<td width='50%'><span class='label'>{label}</span><span class='value'>{format_npr_currency(amount)}</span></td>",
                        )
                else:
                    html_parts.append("<td></td>")  # Empty cell if odd number
            html_parts.append("</tr>")

        html_parts.append("</table>")  # End table
        html_parts.append("</div>")  # End section-box

    def _add_fuel_quantities(self, html_parts: list[str]) -> None:
        """Adds the fuel and goods quantities section using table-based card layout."""
        html_parts.append('<div class="section-box">')
        html_parts.append("<h2>Fuel and Goods Quantities</h2>")

        def get_quantity(key: str) -> float:
            return _get_summary_value(self.summary_data, SUMMARY_KEYS[key], 0) or 0

        cards = [
            {
                "label": "Diesel Sales",
                "value": get_quantity("DIESEL_SALES_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Petrol Sales",
                "value": get_quantity("PETROL_SALES_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Other Fuel Sales",
                "value": get_quantity("OTHER_FUEL_SALES_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Other Goods Sales",
                "value": get_quantity("OTHER_GOODS_SALES_QUANTITY"),
                "unit": "Units",
            },
            {
                "label": "Diesel Purchase",
                "value": get_quantity("DIESEL_PURCHASE_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Petrol Purchase",
                "value": get_quantity("PETROL_PURCHASE_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Other Fuel Purchase",
                "value": get_quantity("OTHER_FUEL_PURCHASE_QUANTITY"),
                "unit": "L",
            },
            {
                "label": "Other Goods Purchase",
                "value": get_quantity("OTHER_GOODS_PURCHASE_QUANTITY"),
                "unit": "Units",
            },
        ]

        non_empty_cards = [c for c in cards if c["value"] > 0]

        if non_empty_cards:
            html_parts.append('<div class="kpi-grid">')
            for card in non_empty_cards:
                html_parts.append('<div class="kpi-card">')
                html_parts.append(f"<strong>{card['label']}</strong>")
                html_parts.append(
                    f"<span>{card['value']:,.2f} {card['unit']}</span>",
                )
                html_parts.append("</div>")
            html_parts.append("</div>")  # Close .kpi-grid
        else:
            html_parts.append(
                "<p>No fuel or goods quantities recorded this period.</p>",
            )

        html_parts.append("</div>")  # Close section-box

    def _create_transaction_table(
        self,
        title: str,
        transactions: list[dict[str, Any]],
    ) -> str:
        """Generates an HTML table for transactions."""
        if not transactions:
            return f"<h3>{title}</h3><p class='note'>No data available for this section.</p>"

        table_html = [f"<h3>{title}</h3>"]
        table_html.append("<table><thead><tr>")
        headers = ["Bill Date", "Transaction ID", "Party", "Grand Total"]
        for header in headers:
            table_html.append(f"<th>{header}</th>")
        table_html.append("</tr></thead><tbody>")

        for tx in transactions:
            table_html.append("<tr>")
            table_html.append(f"<td>{_format_date(tx.get('Bill Date'))}</td>")
            table_html.append(f"<td>{tx.get('Transaction ID', 'N/A')}</td>")
            table_html.append(f"<td>{tx.get('Bill Receiveable Person', 'N/A')}</td>")
            table_html.append(
                f"<td>{format_npr_currency(tx.get('Grand Total', 0))}</td>",
            )
            table_html.append("</tr>")
        table_html.append("</tbody></table>")
        return "\n".join(table_html)

    def _add_top_transactions(self, html_parts: list[str]) -> None:
        """Adds the top transactions section."""
        html_parts.append('<div class="section-box">')  # New section box
        html_parts.append("<h2>Top Transactions</h2>")
        html_parts.append('<div class="section">')  # Group this section
        html_parts.append(
            self._create_transaction_table(
                "Top 5 Sales Transactions",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_TRANSACTIONS"],
                    [],
                ),
            ),
        )
        html_parts.append(
            self._create_transaction_table(
                "Top 5 Purchase Transactions",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_TRANSACTIONS"],
                    [],
                ),
            ),
        )
        html_parts.append("</div>")  # Close section
        html_parts.append("</div>")  # Close section-box

    def _create_top_list_table(
        self,
        title: str,
        data: dict[str, Any],
        value_label: str = "Amount",
    ) -> str:
        """Generates an HTML table for top customers/suppliers/items."""
        if not data:
            return f"<h3>{title}</h3><p class='note'>No data available for this section.</p>"

        html = [f"<h3>{title}</h3>", "<table>"]
        html.append(
            "<thead><tr>"
            "<th style='width:70%;'>Name</th>"
            f"<th style='width:30%;'>{value_label}</th>"
            "</tr></thead>",
        )
        html.append("<tbody>")

        for key, value in data.items():
            formatted_value = (
                format_npr_currency(value)
                if isinstance(value, int | float)
                else str(value)
            )
            html.append(f"<tr><td>{key}</td><td>{formatted_value}</td></tr>")

        html.append("</tbody></table>")
        return "\n".join(html)

    def _add_top_entities(self, html_parts: list[str]) -> None:
        """Adds the top customers, suppliers, and items section."""
        html_parts.append('<div class="section-box">')  # New section box
        html_parts.append("<h2>Top Customers, Suppliers, and Items</h2>")
        html_parts.append('<div class="section">')  # Group this section
        html_parts.append(
            self._create_top_list_table(
                "Top 5 Sales Customers",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_CUSTOMERS"],
                    {},
                ),
                "Sales Amount",
            ),
        )
        html_parts.append(
            self._create_top_list_table(
                "Top 5 Purchase Suppliers",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_SUPPLIERS"],
                    {},
                ),
                "Purchase Amount",
            ),
        )
        html_parts.append(
            self._create_top_list_table(
                "Top 5 Sales Items",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_SALES_ITEMS"],
                    {},
                ),
                "Sales Amount",
            ),
        )
        html_parts.append(
            self._create_top_list_table(
                "Top 5 Purchase Items",
                _get_summary_value(
                    self.summary_data,
                    SUMMARY_KEYS["TOP_5_PURCHASE_ITEMS"],
                    {},
                ),
                "Purchase Amount",
            ),
        )
        html_parts.append("</div>")  # Close section
        html_parts.append("</div>")  # Close section-box

    def _add_cancelled_transactions(self, html_parts: list[str]) -> None:
        """Adds the cancelled transactions summary and details."""
        html_parts.append('<div class="section-box">')  # New section box
        html_parts.append("<h2>Cancelled Transactions Summary</h2>")
        html_parts.append('<div class="section">')  # Group this section
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
            html_parts.append(
                f"<p><strong>Total Cancelled Transactions:</strong> {total_cancelled}</p>",
            )

            table_html = ["<h3>Cancelled Transactions Details:</h3><table><thead><tr>"]
            headers = [
                "Date",
                "Transaction ID",
                "Party",
                "Type",
                "Grand Total",
                "Reason",
            ]
            for header in headers:
                table_html.append(f"<th>{header}</th>")
            table_html.append("</tr></thead><tbody>")

            for tx in cancelled_tx_list:
                table_html.append("<tr>")
                table_html.append(
                    f"<td>{_format_date(tx.get('Cancellation_Date'))}</td>",
                )
                table_html.append(f"<td>{tx.get('Transaction ID', 'N/A')}</td>")
                table_html.append(
                    f"<td>{tx.get('Bill_Receiveable_Person', 'N/A')}</td>",
                )
                table_html.append(
                    f"<td>{tx.get('Transaction_Type_Symbol', 'N/A')}</td>",
                )
                table_html.append(
                    f"<td>{format_npr_currency(tx.get('Transaction_Grand_Total', 0))}</td>",
                )
                table_html.append(f"<td>{tx.get('Why_Update', 'N/A')}</td>")
                table_html.append("</tr>")
            table_html.append("</tbody></table>")
            html_parts.append("\n".join(table_html))
        else:
            html_parts.append(
                "<p class='note'>No cancelled transactions for this period.</p>",
            )
        html_parts.append("</div>")  # Close section
        html_parts.append("</div>")  # Close section-box

    def format_report(self) -> str:
        """Generates the HTML report string."""
        html_parts = []

        html_parts.append("<!DOCTYPE html><html><head>")
        html_parts.append(
            "<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        )
        html_parts.append(
            f"<title>VAT Analytics Report - {self.filing_month_name}</title>",
        )
        html_parts.append(self.HTML_STYLES)
        html_parts.append("</head><body>")
        html_parts.append('<div class="container">')

        self._add_header(html_parts)
        self._add_vat_highlight(html_parts)
        self._add_financial_summary(html_parts)
        self._add_fuel_quantities(html_parts)
        self._add_top_transactions(html_parts)
        self._add_top_entities(html_parts)
        self._add_cancelled_transactions(html_parts)

        # Add Footer
        html_parts.append(
            f"""
            <div class="footer">
                <p>This report was automatically generated by your VAT Reporting Tool.</p>
                <p>&copy; {datetime.datetime.now(tz=datetime.UTC).year} All rights reserved.</p>
            </div>
        """,
        )

        html_parts.append("</div>")  # Close container
        html_parts.append("</body></html>")

        full_html_string = "\n".join(html_parts)
        inlined_html = transform(full_html_string)

        return inlined_html
