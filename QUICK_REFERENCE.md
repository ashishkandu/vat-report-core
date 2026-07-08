# VAT Report System - Key Capabilities Quick Reference

## 🚀 Reporting Modes

### Single-Month Mode
```bash
vat-cli run --month 2081-04
```
**Uses:** IRD Excel templates (Forms 3 & 4)  
**Output:** Purchase, Sales, Lakh Transactions reports  
**Use Case:** Monthly VAT filing

### Fiscal-Year Mode
```bash
vat-cli run --fiscal-year 2081-82
```
**Range:** Shrawan (month 4) to Asar (month 3)  
**Output:** consolidated_purchases_*.xlsx + consolidated_sales_*.xlsx  
**Use Case:** Annual/quarterly consolidated reporting

### Custom Date Range Mode
```bash
vat-cli run --date-range 2081-04 2081-06
```
**Range:** Any consecutive months  
**Output:** Consolidated purchase/sales files  
**Use Case:** Custom period analysis

---

## 🔍 Data Processing Pipeline

```
Raw Transaction Data
    ↓
[Status Filter] → Keep only Status = '001-00' (discard canceled)
    ↓
[Type Separation] → Purchase (Type 1) vs Sales (Type 2)
    ↓
[Period Tracking] → Add reporting_period column
    ↓
[Excel Export] → Two files with summary sheets
```

---

## 📋 CLI Options at a Glance

| Option | Format | Example | Purpose |
|--------|--------|---------|---------|
| `--month` | YYYY-MM | `2081-04` | Single month with templates |
| `--fiscal-year` | YYYY-YY | `2081-82` | Full fiscal year (consolidated) |
| `--date-range` | YYYY-MM YYYY-MM | `2081-04 2081-06` | Custom months (consolidated) |
| `--select-month` | N/A | N/A | Interactive selection |
| `--current` | N/A | N/A | Current month |
| `--previous` | N/A | N/A | Previous month |
| `--dry-run` | N/A | N/A | Simulation (no commits) |
| `--debug` | N/A | N/A | Verbose logging |

---

## 📁 Output Files

### Single-Month Mode
```
data/reports/YYYY-YY/Month/
├── FormA_Purchase_Report_YYYYMM.xlsx
├── FormB_Sales_Report_YYYYMM.xlsx
├── LakhTransactions_YYYYMM.xlsx
└── summary_analytics_Month.html
```

### Consolidated Mode
```
data/reports/
├── consolidated_purchases_YYYY-MM_to_YYYY-MM.xlsx
│   ├── Purchases (data sheet)
│   └── Summary (metrics sheet)
└── consolidated_sales_YYYY-MM_to_YYYY-MM.xlsx
    ├── Sales (data sheet)
    └── Summary (metrics sheet)
```

---

## 🛠️ Common Tasks

### Generate fiscal year 2081-82 without distribution
```bash
vat-cli run --fiscal-year 2081-82 --dry-run
```

### Generate 3-month consolidated report with analytics
```bash
vat-cli run --date-range 2081-04 2081-06 \
  --output-analytics-to-console \
  --save-excel-locally
```

### Generate with debug logging
```bash
vat-cli --debug run --fiscal-year 2081-82
```

### Generate and upload to Google Drive
```bash
vat-cli run --fiscal-year 2081-82 \
  --upload-to-gdrive \
  --send-email
```

### Generate for current month
```bash
vat-cli run --current
```

---

## 📊 Data Schema

### Transaction Columns (Important for Filtering)
- **Status** — '001-00' = valid, others = canceled
- **Transaction Type** — 1 = Purchase, 2 = Sales
- **Grand Total** — Amount in transaction
- **VATABLE AMOUNT** — Taxable portion
- **VAT AMOUNT** — Tax portion
- **reporting_period** — (Added in consolidated mode) Month name

### Consolidation Summary Metrics
- Total Transactions (per type)
- Total Amount (Grand Total sum)
- Total Taxable Amount (VATABLE AMOUNT sum)
- Total Tax Amount (VAT AMOUNT sum)
- Reporting Period (date range label)

---

## ⚠️ Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid fiscal year format` | Wrong format | Use `YYYY-YY` e.g., `2081-82` |
| `Invalid date range format` | Wrong month format | Use `YYYY-MM` e.g., `2081-04` |
| `End month before start month` | Date order wrong | Ensure start ≤ end |
| `No transactions found` | No data in period | Check database restore |
| `Database connection failed` | Config/network issue | Run `vat-cli test-db` |
| `No valid transactions after filtering` | All Status != '001-00' | Check source data |

---

## 🔧 Nepali Fiscal Year Basics

- **Starts:** Shrawan (Month 4)
- **Ends:** Chaitra (Month 3)
- **Format:** `YYYY-YY` where YYYY is Nepali start year
- **Example:** `2081-82` = 2081/04 to 2082/03 = Shrawan 2081 to Asar 2082

### Month Numbers
| Num | Name | Gregorian | Days |
|-----|------|-----------|------|
| 1 | Baishakh | Apr-May | 31 |
| 2 | Jestha | May-Jun | 31 |
| 3 | Asar | Jun-Jul | 31 |
| 4 | Shrawan | Jul-Aug | 31 |
| 5 | Bhadra | Aug-Sep | 31 |
| 6 | Asoj | Sep-Oct | 29/30 |
| 7 | Kartik | Oct-Nov | 29/30 |
| 8 | Mangsir | Nov-Dec | 29/30 |
| 9 | Poush | Dec-Jan | 29/30 |
| 10 | Magh | Jan-Feb | 29/30 |
| 11 | Falgun | Feb-Mar | 29/30 |
| 12 | Chaitra | Mar-Apr | 32/33 |

---

## 🎯 When to Use Each Mode

### Single-Month (--month)
✓ Monthly VAT filing  
✓ Needs IRD-compliant templates  
✓ Standard regulatory reporting  
✗ Not for multi-month analysis  

### Fiscal-Year (--fiscal-year)
✓ Annual consolidated reporting  
✓ Full fiscal year analysis  
✓ Quarterly/semi-annual reviews  
✓ Consolidated purchase/sales tracking  
✗ Not for single-month filing  

### Date-Range (--date-range)
✓ Custom period analysis  
✓ Specific month ranges (e.g., Q1, Q2)  
✓ Ad-hoc reporting periods  
✓ Testing specific periods  
✗ Not for standard fiscal year  

---

## 📞 Support & Debugging

### Enable Debug Mode
```bash
vat-cli --debug run --fiscal-year 2081-82 --dry-run
```
Shows verbose logging for all operations.

### Test Database Connection
```bash
vat-cli test-db
```
Validates SQL Server connectivity.

### Dry-Run Mode
```bash
vat-cli run --fiscal-year 2081-82 --dry-run
```
- ✓ Creates local Excel files
- ✗ Skips database restore
- ✗ Skips Google Drive upload
- ✗ Skips email sending

### View Configuration
```bash
vat-cli config
```
Displays current settings (paths, database, etc.).

---

## 🔐 Configuration Requirements

### Database
- SQL Server with VAT transaction data
- Connection configured in `SharedSettings`
- Backup/restore support for data isolation

### Google Drive (Optional)
- OAuth 2.0 credentials via `client_secrets.json`
- Tokens stored in `.gdrive_tokens/` (per-account)
- Folder structure for organized uploads

### Email (Optional)
- SMTP configuration in `SharedSettings`
- Email templates for distribution

---

## 📖 For More Details

See full documentation in:
- **README.md** — Complete user guide and architecture
- **Workflow Details** — Step-by-step process explanations
- **Troubleshooting** — Error resolution guide
- **Development & Extending** — API usage and customization
