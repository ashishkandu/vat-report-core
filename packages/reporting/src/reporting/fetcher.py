import pandas as pd
from sqlalchemy import Engine, text

SQL_QUERY = """
    SELECT SystemTransaction.[Bill Date],
       SystemTransaction.[Transaction Date],
       CONCAT_WS('.', CalanderDate.[Year], CalanderDate.[Month], CalanderDate.[Day]) AS 'Nepali Date',
       SystemTransaction.[Transaction ID],
       SystemTransaction.[Bill Receiveable Person],
       AccountProfileProduct.[Vat Pan No],
       InventoryItem.[Inventory Name],
       SUM(PurchaseSalesItem.[Item In]) AS 'In',
       SUM(PurchaseSalesItem.[Item Out]) AS 'Out',
       InventoryUnit.Symbol,
       PurchaseSalesAmount.[Grand Total], -- Transaction level total
       PurchaseSalesAmount.[Round Off], -- Transaction level Round off amount
       (PurchaseSalesItem.[VATABLE AMOUNT] + PurchaseSalesItem.[VAT AMOUNT]) AS 'Item Total',
       PurchaseSalesItem.[VATABLE AMOUNT], -- Item level
       PurchaseSalesItem.[VAT AMOUNT], -- Item level
       SystemTransaction.[Reference No],
       SystemTransaction.Status,
       ModifiedInfo.[Why Update],
       SystemTransaction.[Transaction Type] -- Added to filter in Python 1 = Purchase, 2 = Sales
        FROM [VatBillingSoftware].[dbo].[SystemTransaction] SystemTransaction
        JOIN [VatBillingSoftware].[dbo].[SystemTransactionPurchaseSalesItem] PurchaseSalesItem
            ON PurchaseSalesItem.[Transaction ID] = SystemTransaction.[Transaction ID]
        JOIN [VatBillingSoftware].[dbo].[SystemTransactionPurchaseSalesAmount] PurchaseSalesAmount
            ON PurchaseSalesAmount.[Transaction ID] = SystemTransaction.[Transaction ID]
        JOIN [VatBillingSoftware].[dbo].[AccountProfileProduct] AccountProfileProduct
            ON AccountProfileProduct.[ACCOUNT ID] = PurchaseSalesAmount.[Account ID]
        JOIN [VatBillingSoftware].[dbo].[InventoryItem] InventoryItem
            ON InventoryItem.[Inventory ID] = PurchaseSalesItem.[Inventory Item Code]
        JOIN [VatBillingSoftware].[dbo].[SystemCalenderDate] CalanderDate
            ON CalanderDate.[English Date] = SystemTransaction.[Bill Date]
        LEFT JOIN [VatBillingSoftware].[dbo].[SystemModifiedInformation] ModifiedInfo
            ON ModifiedInfo.[Primary Key ID] = SystemTransaction.[Transaction ID]
        LEFT JOIN [VatBillingSoftware].[dbo].[InventoryUnitCreation] InventoryUnit
            ON InventoryUnit.[Row ID] = PurchaseSalesItem.[Unit Id]
        WHERE SystemTransaction.[Bill Date] BETWEEN :start_date AND :end_date
            AND SystemTransaction.[Transaction Type] IN (1, 2)
        GROUP BY SystemTransaction.[Transaction ID],
                SystemTransaction.[Bill Date],
                SystemTransaction.[Transaction Date],
                CalanderDate.[Year], CalanderDate.[Month], CalanderDate.[Day],
                SystemTransaction.[Bill Receiveable Person],
                AccountProfileProduct.[Vat Pan No],
                InventoryUnit.Symbol,
                PurchaseSalesAmount.[Grand Total],
                PurchaseSalesAmount.[Round Off],
                PurchaseSalesItem.[VATABLE AMOUNT],
                PurchaseSalesItem.[VAT AMOUNT],
                SystemTransaction.[Reference No],
                SystemTransaction.Status,
                InventoryItem.[Inventory Name],
                ModifiedInfo.[Why Update],
                SystemTransaction.[Transaction Type]
        ORDER BY SystemTransaction.[Bill Date];
"""


def fetch_raw_transaction_dataframe(
    engine: Engine,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    with engine.connect() as conn:
        transactions_df = pd.read_sql_query(
            text(SQL_QUERY),
            conn,
            params={"start_date": start_date, "end_date": end_date},
        )
    return transactions_df
