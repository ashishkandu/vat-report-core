# README.md Update Summary

## Overview
Updated the VAT Report System README.md to comprehensively document the new **fiscal-year** and **multi-month consolidation** features, along with architectural details and troubleshooting guidance.

**File Size:** 388 lines (expanded from ~200 original lines)

## Key Sections Added/Updated

### 1. **Overview Section** ✅
- Updated to highlight **dual-mode support**: single-month and fiscal-year reporting
- Clarified that system supports both traditional monthly VAT filings AND consolidated multi-month reports

### 2. **Features Section** ✅
Expanded with comprehensive feature list:
- **Flexible Reporting Periods:** Single-month, fiscal-year, custom date-range
- **Data Cleaning & Processing:** Added Status filtering and Transaction Type differentiation
- **Report Generation:** Distinct documentation for single-month (template-based) vs. fiscal-year (consolidated)
- **Workflow Orchestration:** Month, fiscal-year, and date-range CLI options
- **Distribution:** Email and Google Drive support with attachments

### 3. **Usage Section** ✅
Replaced generic examples with **four specific command variations**:
```sh
vat-cli run                                    # Previous month (default)
vat-cli run --month 2081-04                   # Specific month
vat-cli run --fiscal-year 2081-82             # Full fiscal year
vat-cli run --date-range 2081-04 2081-06      # Custom range
vat-cli run --select-month                    # Interactive selection
```

### 4. **CLI Usage Section** ✅
Completely restructured with detailed documentation:

#### New subsections:
- **Main Workflow: `vat-cli run`** — Comprehensive explanation
- **Common Options** — All shared flags documented
- **Period Selection Options** — Mutually exclusive month/fiscal-year/date-range/current/previous/select-month
  - `-m, --month TEXT` → Single-month with IRD templates
  - `-f, --fiscal-year TEXT` → Consolidated without templates (NEW)
  - `-d, --date-range TEXT TEXT` → Custom period (NEW)
  - `-s, --select-month` → Interactive selection
  - `--current`, `--previous` → Current/previous month shortcuts

#### Examples subsection (NEW):
- Single-month example with `--month 2081-04`
- Fiscal-year example with `--fiscal-year 2081-82`
- Date-range example with `--date-range 2081-04 2081-06`
- Interactive selection example

### 5. **Workflow Details Section** ✅ (NEW)

#### Single-Month Workflow:
5-step process with IRD template generation (Forms 3 & 4)

#### Fiscal-Year / Multi-Month Consolidation Workflow:
7-step process detailing:
1. Fetch raw transactions for ALL months in range
2. Consolidate with period tracking
3. **Status filtering (001-00)** → Key feature documentation
4. Separate Purchase (Type 1) vs Sales (Type 2)
5. Generate two consolidated Excel files WITHOUT templates
6. Optional analytics output
7. Optional GDrive/email distribution

#### Data Filtering & Validation (NEW):
- Status = '001-00' requirement (discards canceled)
- Period tracking column in output
- Logging of filtered transactions

#### Nepali Fiscal Year (NEW):
- Definition: Shrawan (month 4) to Chaitra (month 3)
- Example: 2081-82 = Shrawan 2081 to Asar 2082
- Format specifications: YYYY-YY vs YYYY-MM

### 6. **Key Packages & Modules Section** ✅ (Expanded)

Added NEW entries:
- `src/vat_report/fiscal_year_workflow.py` — Multi-month orchestration
- `packages/reporting/src/reporting/fiscal_year.py` — FiscalYearRange class
- `packages/reporting/src/reporting/fetcher.py` — SQL Server data queries
- `packages/nepalidates/src/nepalidates/filing_month.py` — Month iteration (.next())
- Updated reference to `packages/shared/src/shared/constants.py` for FISCAL_YEAR_* enums

### 7. **Development & Extending Section** ✅ (Enhanced)

#### New subsections:
- **Adding New Report Types** — 4-step guide
- **Generating Fiscal-Year Reports Programmatically** (NEW)
  ```python
  fiscal_range = FiscalYearRange.from_fiscal_year("2081-82")
  # or
  fiscal_range = FiscalYearRange.from_date_range("2081-04", "2081-06")
  execute_fiscal_year_workflow(fiscal_range, ...)
  ```
- **Iterating Through Months** (NEW)
  ```python
  month = FilingMonth(2081, 4)
  while month <= FilingMonth(2081, 6):
      month = month.next()
  ```
- **Customizing Data Processing** — Consolidation extension points
- **Adding New Output Formats** — Formatter implementation pattern

### 8. **Troubleshooting Section** ✅ (NEW - 45+ lines)

#### Common Issues with solutions:
1. **Invalid fiscal year format** — YYYY-YY format requirement
2. **Invalid month format** — YYYY-MM format requirement
3. **End month before start month** — Date range validation
4. **No transactions found** — Database/period verification
5. **Database connection failed** — Configuration & connection testing
6. **No valid transactions after status filtering** — Expected condition

#### Debug Mode section:
```sh
vat-cli --debug run --fiscal-year 2081-82 --dry-run
```

#### Dry-Run Mode section:
Detailed explanation of what's skipped vs. created during dry runs

### 9. **Architecture Notes Section** ✅ (NEW - 25+ lines)

#### Single-Month vs. Consolidated Workflows:
- Single-month: Template-based, traditional monthly structure
- Consolidated: Generic files, multi-month analysis capability

#### Transaction Filtering Pipeline:
3-step sequential filtering:
1. Status filter (001-00)
2. Type filter (Purchase vs Sales)
3. Aggregation

#### Performance Considerations:
- pandas DataFrame efficiency
- Direct Excel writing (no full file loading)
- Optimized database queries
- `--dry-run` for large ranges

## Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Lines | ~200 | 388 | +94% |
| Sections | ~8 | 15 | +87% |
| Code Examples | 2 | 15+ | +650% |
| Fiscal-Year Documentation | None | ~150 lines | NEW |
| CLI Option Documentation | Minimal | Comprehensive | Expanded |

## Coverage of New Features

✅ **Fiscal-Year Support:**
- Format specification (YYYY-YY)
- Month range calculation (month 4-3)
- Consolidation workflow explanation
- CLI option documentation with examples

✅ **Status Filtering:**
- Requirement (001-00 only)
- Automatic discarding of canceled transactions
- Logging of filtered counts
- Data pipeline documentation

✅ **Multi-Month Consolidation:**
- Two Excel files (purchase/sales)
- Period tracking column
- Summary sheets per file
- No template downloads needed

✅ **Architecture:**
- Differences between single-month and consolidated workflows
- Data filtering pipeline
- Performance considerations
- Extension points for customization

✅ **Troubleshooting:**
- 6 common error scenarios
- Debug and dry-run modes
- Format validation
- Database verification

## Files Modified

- **README.md** — Complete rewrite with expanded sections (+188 lines)

## Related Implementation Files (Documented in README)

- `src/vat_report/fiscal_year_workflow.py` — Fiscal-year orchestration
- `packages/reporting/src/reporting/fiscal_year.py` — FiscalYearRange class
- `packages/cli/src/cli/main.py` — CLI option handling
- `packages/nepalidates/src/nepalidates/filing_month.py` — Month utilities

## Next Steps (If Needed)

- [ ] Add TypeScript/API documentation for programmatic usage
- [ ] Create CHANGELOG.md documenting fiscal-year feature addition
- [ ] Add example output screenshots or HTML reports
- [ ] Create separate developer guide for advanced customization
- [ ] Add performance benchmarks for large date ranges
