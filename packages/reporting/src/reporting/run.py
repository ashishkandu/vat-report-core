from dbkit.engine import get_engine
from shared import SharedSettings

from .fetcher import fetch_raw_transaction_dataframe
from .processor import (
    LakhTransactionsReport,
    PurchaseReport,
    SalesReport,
    _clean_and_prepare_dataframe,
    generate_summary_analytics,
)

settings = SharedSettings()


def run() -> None:
    engine = get_engine(settings.TARGET_DATABASE)
    raw_transactions_df = fetch_raw_transaction_dataframe(
        engine,
        "2024-11-16",
        "2024-12-15",
    )
    print(
        f"Raw data fetched: {raw_transactions_df.shape[0]} rows, {raw_transactions_df.shape[1]} columns",
    )

    # Clean and prepare the data once
    processed_df = _clean_and_prepare_dataframe(raw_transactions_df)

    # --- Generate Reports using the new classes ---
    # Instantiate report objects
    purchase_report = PurchaseReport()
    sales_report = SalesReport()
    lakh_transactions_report = LakhTransactionsReport()

    # Generate the DataFrames by calling the generate_dataframe method
    purchase_report_df = purchase_report.generate_dataframe(processed_df)
    sales_report_df = sales_report.generate_dataframe(processed_df)
    lakh_transactions_report_df = lakh_transactions_report.generate_dataframe(
        processed_df,
    )

    print("\n--- Report DataFrames Ready ---")
    print(f"{purchase_report.sheet_name} DF Head:\n", purchase_report_df.head())
    print(f"{sales_report.sheet_name} DF Head:\n", sales_report_df.head())
    print(
        f"{lakh_transactions_report.sheet_name} DF Head:\n",
        lakh_transactions_report_df.head(),
    )

    # Generate summaries
    summary_analytics = generate_summary_analytics(processed_df)
    print("\n--- Summary Analytics Ready ---")
    for key, value in summary_analytics.items():
        # Format numbers for better readability
        if isinstance(value, int | float):
            print(f"{key}: {value:,.2f}")
        elif isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, int | float):
                    print(f"  {sub_key}: {sub_value:,.2f}")
                else:
                    print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")
