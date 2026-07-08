# VAT Report Automation System

## Security & Architecture Note

This repository represents the public distribution version of the `vat-report` application. 

To adhere to industry-standard security compliance and protect internal firm infrastructure, this repository has been explicitly decoupled from its operational environment. The commit history has been flattened to separate the core engineering logic from private deployment pipelines, automated cron runners, and internal environmental configurations.

## Overview

This project is a modular, multi-package Python monorepo for automating the generation, analysis, and distribution of VAT (Value Added Tax) reports for Nepali businesses. It supports both **single-month** and **fiscal-year consolidated** reporting. The system fetches transaction data from a SQL Server database, processes and summarizes it, generates Excel and HTML reports, and can email or upload them to Google Drive. It is designed for both scheduled (e.g., GitHub Actions) and manual operation.

## Features

- **Flexible Reporting Periods:**
  - Single-month reports (traditional monthly VAT filings)
  - Fiscal-year consolidated reports (Shrawan to Asar across fiscal years, e.g., 2081-82)
  - Custom date-range reports (any arbitrary period of consecutive months)

- **Automated Data Fetching:** Connects to a SQL Server database to fetch raw transaction data for specified Nepali filing months.

- **Data Cleaning & Processing:**
  - Cleans and processes raw data into structured DataFrames
  - Filters to valid transactions only (Status = '001-00'), discards canceled rows
  - Differentiates between Purchase (Type 1) and Sales (Type 2) transactions

- **Report Generation:**
  - **Single-Month:** Generates IRD-compliant Excel reports (Purchase, Sales, Lakh Transactions) using templates
  - **Fiscal-Year/Multi-Month:** Consolidates transactions across months into unified purchase and sales Excel files (without templates)
  - Produces summary analytics in console and HTML formats for all periods

- **Distribution:**
  - Emails reports to stakeholders with file attachments
  - Uploads reports to Google Drive
  - Supports dry-run mode for testing without committing changes

- **Workflow Orchestration:**
  - Flexible CLI with month, fiscal-year, and date-range options
  - Manual month selection with interactive prompts
  - Supports dry-run mode and extensive logging
  - Can be run as a CLI or scheduled via GitHub Actions

- **Extensible & Modular:**
  - Each major function (fetching, processing, formatting, consolidation, emailing, uploading) is a separate package/module
  - Easy to add new report types or integrations

## Monorepo Structure

```
vat-report/
├── packages/
│   ├── cli/           # CLI entrypoints and commands
│   ├── dbkit/         # Database connection utilities
│   ├── downloader/    # IRD template and backup downloaders
│   ├── drive/         # Google Drive upload logic
│   ├── file_operations/ # Disk I/O helpers
│   ├── ird_client/    # IRD API integrations (if any)
│   ├── mailer/        # Email sending logic
│   ├── nepalidates/   # Nepali date utilities (FilingMonth, etc.)
│   ├── reporting/     # Core reporting logic (fetch, process, format, export)
│   ├── restorer/      # Database restore logic
│   ├── shared/        # Shared settings, constants, logging, utils
│   ├── uploader/      # Upload manager (Google Drive, etc.)
├── src/vat_report/    # Main workflow orchestration
├── data/              # Backups, downloads, and generated reports
├── pyproject.toml     # Monorepo/project config
├── README.md          # This file
```

## Quick Start

### Prerequisites
- Python 3.13+
- SQL Server database with VAT transaction data
- IRD Excel templates (auto-downloaded)
- Google Drive and email credentials (for uploads/emails)

### Installation (Development)

1. **Clone the repo:**
   ```sh
   git clone <repo-url>
   cd vat-report
   ```
2. **Install dependencies:**
   ```sh
   pip install -e .
   # Or use your preferred monorepo tool (e.g., uv, pip, hatch)
   ```
3. **Configure environment:**
   - Create `client_secrets.json` from your Google Cloud OAuth credentials (see [Google Drive OAuth Setup](#google-drive-oauth-setup) below)
   - Set up `.env` or environment variables for database and API configs (see [Configuration](#configuration))

### Usage

#### CLI
Run the main workflow for the previous month:
```sh
vat-cli run
```

Run for a specific month:
```sh
vat-cli run --month 2081-04
```

Run for an entire fiscal year (Shrawan to Chaitra):
```sh
vat-cli run --fiscal-year 2081-82
```

Run for a custom date range (any consecutive months):
```sh
vat-cli run --date-range 2081-04 2081-06
```

Or use interactive month selection:
```sh
vat-cli run --select-month
```

See full CLI usage below for all options and other commands.

### CLI Usage

The main entrypoint is `vat-cli`. Use `--help` for all options and subcommands.

#### Main Workflow: `vat-cli run`

Run the full VAT reporting workflow for the specified period (month, fiscal year, or date range).

##### Common Options for `vat-cli run`
- `-p, --pan TEXT` — Override the PAN number from settings (for multi-company setups).
- `-o, --office-name TEXT` — Override the office name from settings.
- `--dry-run` — Simulate the workflow without making permanent changes (no DB restore, uploads, or emails).
- `--output-analytics-to-console/--no-output-analytics-to-console` — Output analytics summary to console (default: True).
- `--save-analytics-html-locally/--no-save-analytics-html-locally` — Save analytics HTML report locally (default: True).
- `--upload-to-gdrive` — Upload generated reports and backups to Google Drive (requires Google Drive API setup).
- `--send-email` — Send an email with reports (requires SMTP email configuration).
- `--save-excel-locally/--no-save-excel-locally` — Save generated Excel reports locally (default: True).

##### Period Selection Options (mutually exclusive)
- `-m, --month TEXT` — Specific month in BSYYYY-MM format (e.g., `2081-02`). Generates single-month reports with IRD templates.
- `-f, --fiscal-year TEXT` — Entire fiscal year in YYYY-YY format (e.g., `2081-82`). Generates consolidated purchase/sales files without templates. Fiscal year spans Shrawan (month 4) of start year through Chaitra (month 3) of end year.
- `-d, --date-range TEXT TEXT` — Custom date range with two BSYYYY-MM dates (e.g., `2081-04 2081-06`). Generates consolidated files for the specified months.
- `-s, --select-month [BSYYYY-MM|SELECT]` — Interactively select a filing month from a list. Can also pass 'current', 'previous', a list number, or BSYYYY-MM directly.
- `--current` — Use the current filing month.
- `--previous` — Use the previous filing month (default if no period option provided).

##### Examples

Single-month report for Shrawan 2081:
```sh
vat-cli run --month 2081-04 --dry-run
```

Fiscal-year consolidated report for 2081-82 (Shrawan 2081 - Asar 2082):
```sh
vat-cli run --fiscal-year 2081-82 --save-excel-locally --output-analytics-to-console
```

Custom date range (Shrawan through Aswin 2081):
```sh
vat-cli run --date-range 2081-04 2081-06 --upload-to-gdrive --send-email
```

Interactive month selection:
```sh
vat-cli run --select-month
```

#### Other Commands
- `vat-cli analytics` — Generate and print summary analytics for a specified month or period.
- `vat-cli export-report` — Export a specific report type (purchase, sales, lakh-transactions) to Excel for a month.
- `vat-cli download-templates` — Download IRD Excel templates for report generation.
- `vat-cli rotate-backups` — Rotate old database backups based on retention policy.
- `vat-cli restore-db` — Restore the database from a specified backup file.
- `vat-cli filing-month` — Show details about a specific filing month (name, fiscal year, date range, etc.).
- `vat-cli config` — Print current application configuration.
- `vat-cli test-db` — Test the connection to the configured database.
- `vat-cli shell` — Start an interactive Python shell with pre-imported project context.
- `vat-cli generate-reports` — Generate VAT reports and analytics for a selected month (database must be ready).

For details on each command and its options, use:
```sh
vat-cli <command> --help
```

#### Python API
You can import and run the workflow in your own scripts:
```python
from vat_report import main
main()
```

## Workflow Details

### Single-Month Workflow
When you run `vat-cli run --month <month>` (or use month-selection options):
1. Fetch raw transaction data from the database for the specified month
2. Clean and process data into structured DataFrames
3. Generate IRD-compliant Excel reports using downloaded templates:
   - Purchase Report (Form 3)
   - Sales Report (Form 4)
   - Lakh Transactions Report
4. Generate summary analytics in console and/or HTML format
5. Optionally upload to Google Drive and/or email the reports

### Fiscal-Year / Multi-Month Consolidation Workflow
When you run `vat-cli run --fiscal-year <year>` or `--date-range <start> <end>`:
1. Fetch raw transaction data for **all months** in the specified range
2. Consolidate transactions across months with period tracking (which month each transaction belongs to)
3. Filter transactions to **valid status only** (Status = '001-00'), discarding canceled or invalid rows
4. Separate consolidated data into:
   - **Purchase transactions** (Transaction Type = 1)
   - **Sales transactions** (Transaction Type = 2)
5. Generate two consolidated Excel files (without templates):
   - `consolidated_purchases_YYYY-MM_to_YYYY-MM.xlsx` with data and summary sheet
   - `consolidated_sales_YYYY-MM_to_YYYY-MM.xlsx` with data and summary sheet
6. Optionally output analytics to console and/or HTML
7. Optionally upload consolidated files to Google Drive and/or email them

### Data Filtering & Validation
- **Status Filtering:** Only transactions with Status = '001-00' (valid, non-canceled) are included in consolidated reports
- **Canceled Transactions:** Any transaction with a different status code is automatically discarded with logging
- **Period Tracking:** In consolidated reports, each row includes a `reporting_period` column indicating which month the transaction belongs to

### Nepali Fiscal Year
- **Definition:** Nepali fiscal year runs from Shrawan (month 4) to Aswin (month 3)
- **Example:** Fiscal year 2081-82 spans Shrawan 2081 through Aswin 2082
- **Format:** Fiscal years are specified as `YYYY-YY` (e.g., `2081-82`)
- **Month Format:** Individual months use `YYYY-MM` format (e.g., `2081-04` for Shrawan 2081)

#### GitHub Actions
A sample workflow is provided to automate monthly runs (see `.github/workflows/` or your YAML file):
- Scheduled on the 1st of every month
- Supports manual dispatch with options for dry-run and custom month

## Key Packages & Modules

- **src/vat_report/workflow.py:** Single-month workflow orchestration (download, restore, fetch, process, export, email, upload)
- **src/vat_report/fiscal_year_workflow.py:** Fiscal-year/multi-month consolidation workflow (fetch all months, consolidate, filter, export to Excel)
- **packages/reporting/src/reporting/fiscal_year.py:** `FiscalYearRange` class for fiscal year and date range parsing; `FiscalYearReport` base class for consolidated reporting
- **packages/reporting/src/reporting/processor.py:** `BaseReport` and concrete report classes (PurchaseReport, SalesReport, LakhTransactionsReport) for single-month reports; DataFrame processing logic
- **packages/reporting/src/reporting/fetcher.py:** SQL Server data fetching; `fetch_raw_transaction_dataframe()` for querying transactions by date range
- **packages/reporting/src/reporting/formatter/console_formatter.py:** Console analytics formatting and display
- **packages/nepalidates/src/nepalidates/filing_month.py:** `FilingMonth` class for Nepali date handling; methods for month iteration (`.next()`), fiscal year calculation, and date range conversion (BS to AD)
- **packages/shared/src/shared/:** Shared settings, constants, logging utilities, and configuration management
- **packages/shared/src/shared/constants.py:** Report type enums (`CommonReportType`) including `FISCAL_YEAR_PURCHASE`, `FISCAL_YEAR_SALES`, etc.

## Google Drive OAuth Setup

### Overview
This project uses OAuth 2.0 with Google Drive API for uploading reports and downloading backups. Tokens are stored per-account, allowing different Google accounts for uploads (sharing reports) and downloads (accessing backups).

### Prerequisites
- A Google Cloud Project with Drive API enabled
- OAuth 2.0 Client ID (Installed Application type)
- Access to create and manage GitHub Secrets (for CI/CD)

### Step 1: Create a Google Cloud Project & OAuth Client

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Navigate to **APIs & Services** > **Library**
   - Search for "Google Drive API"
   - Click **Enable**
4. Create an OAuth 2.0 Client ID:
   - Go to **APIs & Services** > **Credentials**
   - Click **Create Credentials** > **OAuth 2.0 Client IDs**
   - Choose **Desktop Application** (Installed Application)
   - Name it (e.g., "VAT Report Tool")
   - Click **Create**
5. Download the client secrets file:
   - Click the download icon next to the created credential
   - Save as `client_secrets.json` in the repo root
   - **Add to .gitignore** (it's already ignored by default)

### Step 2: Create OAuth Tokens Locally (Developer Setup)

Run the interactive token creation helper:

#### For Upload Account (sharing reports to Drive)
```sh
uv run vat-cli drive-auth --account upload
```
This will:
- Open your browser to authenticate
- Save the token to `.gdrive_tokens/token_upload.json`

#### For Download Account (accessing backups from Drive)
```sh
uv run vat-cli drive-auth --account download
```
This will:
- Open your browser to authenticate (can be same or different account)
- Save the token to `.gdrive_tokens/token_download.json`

#### For Default Account (if using a single account)
```sh
uv run vat-cli drive-auth
```
This will:
- Save the token to `.gdrive_tokens/token.json`

**Note:** The tokens include a `refresh_token`, which allows non-interactive refreshes. These tokens are **long-lived and should be treated as secrets**. Do not commit them to git.

### Step 3: Configure Environment Variables

Create a `.env` file or set environment variables:

```bash
# Google Drive OAuth configuration
GDRIVE_OAUTH_TOKEN_DIR=.gdrive_tokens           # Directory where tokens are stored
GDRIVE_CREDENTIALS_CLIENT_SECRETS=client_secrets.json  # Path to client secrets
GDRIVE_DEFAULT_OAUTH_ACCOUNT=                    # (optional) Default account alias
GDRIVE_UPLOAD_ACCOUNT=upload                     # Account to use for uploads
GDRIVE_DOWNLOAD_ACCOUNT=download                 # Account to use for downloads

# Google Drive folder configuration
GDRIVE_REPORTS_BASE_FOLDER_ID=                   # (optional) Pre-created folder ID on Drive
GDRIVE_REPORTS_BASE_FOLDER_NAME=VAT Reports      # Folder name (auto-created if not found)
```

### Step 4: Use in Local Commands

Once tokens are created and configured, use the CLI with Google Drive options:

```sh
# Upload generated reports to Google Drive
uv run vat-cli run --month 2081-04 --upload-to-gdrive

# Download backups and upload reports (full workflow)
uv run vat-cli run --fiscal-year 2081-82 --upload-to-gdrive
```

### Step 5: CI/CD Setup (GitHub Actions)

To automate uploads/downloads in GitHub Actions, you need to:

#### 5a. Generate CI Tokens

On your local machine, create fresh tokens for the CI environment:

```sh
# Create or update tokens with offline access
uv run vat-cli drive-auth --account upload
uv run vat-cli drive-auth --account download
```

Ensure the tokens include `refresh_token` by checking the token file:
```sh
cat .gdrive_tokens/token_upload.json
# Should contain: "refresh_token": "..."
```

#### 5b. Encode Secrets as Base64

Convert the credential files to base64 for GitHub Secrets:

```bash
# Encode client secrets
base64 -w 0 client_secrets.json > client_secrets.b64
echo "GOOGLE_CLIENT_SECRET_B64=$(cat client_secrets.b64)" >> $GITHUB_ENV

# Encode upload token
base64 -w 0 .gdrive_tokens/token_upload.json > token_upload.b64
echo "GOOGLE_TOKEN_UPLOAD_B64=$(cat token_upload.b64)" >> $GITHUB_ENV

# Encode download token
base64 -w 0 .gdrive_tokens/token_download.json > token_download.b64
echo "GOOGLE_TOKEN_DOWNLOAD_B64=$(cat token_download.b64)" >> $GITHUB_ENV
```

Or one-liner:
```bash
echo "GOOGLE_CLIENT_SECRET_B64=$(base64 -w 0 < client_secrets.json)"
echo "GOOGLE_TOKEN_UPLOAD_B64=$(base64 -w 0 < .gdrive_tokens/token_upload.json)"
echo "GOOGLE_TOKEN_DOWNLOAD_B64=$(base64 -w 0 < .gdrive_tokens/token_download.json)"
```

#### 5c. Add GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** for each:
   - **Name:** `GOOGLE_CLIENT_SECRET_B64` — Value: base64 output from step 5b
   - **Name:** `GOOGLE_TOKEN_UPLOAD_B64` — Value: base64 output from step 5b
   - **Name:** `GOOGLE_TOKEN_DOWNLOAD_B64` — Value: base64 output from step 5b

#### 5d. Update GitHub Actions Workflow

The workflow (`.github/workflows/vat-report.yml`) already includes a decode step:
```yaml
- name: Decode Google Drive credential files
  run: |
    echo "$GOOGLE_CLIENT_SECRET_B64" | base64 -d > "$GDRIVE_CREDENTIALS_CLIENT_SECRETS"
    mkdir -p "$GDRIVE_OAUTH_TOKEN_DIR"
    echo "$GOOGLE_TOKEN_UPLOAD_B64" | base64 -d > "$GDRIVE_OAUTH_TOKEN_DIR/token_upload.json"
    echo "$GOOGLE_TOKEN_DOWNLOAD_B64" | base64 -d > "$GDRIVE_OAUTH_TOKEN_DIR/token_download.json"
  env:
    GOOGLE_CLIENT_SECRET_B64: ${{ secrets.GOOGLE_CLIENT_SECRET_B64 }}
    GOOGLE_TOKEN_UPLOAD_B64: ${{ secrets.GOOGLE_TOKEN_UPLOAD_B64 }}
    GOOGLE_TOKEN_DOWNLOAD_B64: ${{ secrets.GOOGLE_TOKEN_DOWNLOAD_B64 }}
```

### Troubleshooting OAuth Issues

#### "No valid OAuth token available" Error
- **Cause:** Running non-interactively without a pre-created token file
- **Solution:** 
  - Locally: Run `uv run vat-cli drive-auth --account <name>` to create tokens
  - In CI: Ensure the secrets are correctly encoded and the workflow decodes them to `$GDRIVE_OAUTH_TOKEN_DIR`

#### "Credentials file not found" Error
- **Cause:** `client_secrets.json` not in expected location
- **Solution:** 
  - Ensure `client_secrets.json` is in the repo root or set `GDRIVE_CREDENTIALS_CLIENT_SECRETS` to the correct path
  - In CI, the workflow decodes it automatically if the secret is set

#### "Invalid token / refresh failed" Error
- **Cause:** Token has expired and cannot be refreshed (no refresh_token), or permissions were revoked
- **Solution:**
  - Regenerate the token: `uv run vat-cli drive-auth --account <name>`
  - Ensure the token includes `refresh_token` in the JSON
  - Check that the Google account hasn't revoked permissions

#### Permissions Issues
- **Cause:** The authenticated Google account doesn't have access to the target Drive folder
- **Solution:**
  - Ensure the Google account has Editor or Owner permissions on the Drive folder
  - Verify the folder ID in `GDRIVE_REPORTS_BASE_FOLDER_ID` (if using a pre-created folder)
  - The app automatically creates the folder if not found (default: "VAT Reports")

### Security Best Practices

1. **Never commit tokens to git** — They are already in `.gitignore`
2. **Rotate tokens periodically** — Regenerate and update GitHub Secrets every 6–12 months
3. **Use separate accounts for upload/download** if they have different permissions
4. **Limit Drive folder permissions** — Only grant access to the specific folder, not the entire drive
5. **Audit access logs** in Google Cloud Console periodically
6. **Revoke tokens** if the account is compromised: `uv run vat-cli drive-auth --account <name>` to regenerate

### Using a Single OAuth Account

If you prefer to use the same Google account for both uploads and downloads:

1. Create a single token:
   ```sh
   uv run vat-cli drive-auth
   ```
2. Set environment variable:
   ```bash
   GDRIVE_DEFAULT_OAUTH_ACCOUNT=  # Leave blank to use default token.json
   ```
3. The uploader and downloader will automatically fall back to the default token

### Advanced: Custom Client Secrets per Account

For advanced scenarios (multiple OAuth apps), you can optionally provide per-account client secrets:

```bash
GDRIVE_CLIENT_SECRETS_DIR=.gdrive_secrets  # Directory containing credentials_<account>.json
```

The auth module will first look for `credentials_upload.json` and `credentials_download.json` in this directory, then fall back to the global `client_secrets.json`.

## Configuration
- **Database:** Set `TARGET_DATABASE` and connection info in `SharedSettings` or environment variables.
- **Paths:** Configure backup, download, and report paths in `SharedSettings`.
- **Secrets:** Store sensitive info (DB password, email, Google Drive OAuth tokens) in environment variables or secret files.
- **Google Drive:** See [Google Drive OAuth Setup](#google-drive-oauth-setup) for OAuth token creation and GitHub Secrets configuration.

### Environment Variables Reference
```bash
# Database
TARGET_DATABASE=<database_name>
DB_CONNECTION_STRING=<connection_string>

# Google Drive OAuth
GDRIVE_OAUTH_TOKEN_DIR=.gdrive_tokens
GDRIVE_CREDENTIALS_CLIENT_SECRETS=client_secrets.json
GDRIVE_UPLOAD_ACCOUNT=upload
GDRIVE_DOWNLOAD_ACCOUNT=download
GDRIVE_REPORTS_BASE_FOLDER_NAME=VAT Reports

# Email (if using --send-email)
EMAIL_SENDER=<your_email>
EMAIL_PASSWORD=<app_password>
EMAIL_RECIPIENTS=<comma_separated_emails>
```

## Development & Extending

### Adding New Report Types
1. Subclass `BaseReport` in `packages/reporting/src/reporting/processor.py`
2. Implement the required report generation logic (data filtering, calculations, Excel formatting)
3. Add the new type to the `CommonReportType` enum in `packages/shared/src/shared/constants.py`
4. Register the report in the main workflow (`src/vat_report/workflow.py`)

### Generating Fiscal-Year Reports Programmatically
```python
from reporting.fiscal_year import FiscalYearRange
from vat_report.fiscal_year_workflow import execute_fiscal_year_workflow
from shared import SharedSettings

# Create a fiscal year range
fiscal_range = FiscalYearRange.from_fiscal_year("2081-82")

# Or create a custom date range
fiscal_range = FiscalYearRange.from_date_range("2081-04", "2081-06")

# Execute the workflow
settings = SharedSettings()
execute_fiscal_year_workflow(
    fiscal_range=fiscal_range,
    settings=settings,
    dry_run=False,
    save_excel_locally=True,
    output_analytics_to_console=True,
)
```

### Iterating Through Months
The `FilingMonth` class supports month iteration:
```python
from nepalidates import FilingMonth

month = FilingMonth(2081, 4)  # Shrawan 2081
while month <= FilingMonth(2081, 6):  # Loop until Aswin 2081
    print(f"Processing {month.name} {month.year}")
    month = month.next()  # Move to next month
```

### Customizing Data Processing
The consolidation function in `src/vat_report/fiscal_year_workflow.py` can be extended to:
- Apply additional filtering criteria (e.g., amount thresholds)
- Add custom columns (e.g., period-over-period comparisons)
- Implement different consolidation strategies (e.g., by department, vendor, or item type)

### Adding New Output Formats
Implement new formatters for analytics and reports in `packages/reporting/src/reporting/formatter/` following the existing pattern of `ConsoleReportFormatter` and `HtmlReportFormatter`.

## Troubleshooting

### Common Issues & Solutions

**Invalid fiscal year format:**
```
Error: Invalid fiscal year format. Expected format: YYYY-YY
```
- **Cause:** Fiscal year specified incorrectly
- **Solution:** Use format like `2081-82` (not `2081/82` or `2081`). The first number is the Nepali year, and the second is the year+1 modulo 100.

**Invalid month format:**
```
Error: Invalid date range. Expected format: YYYY-MM
```
- **Cause:** Month specified in wrong format
- **Solution:** Use format like `2081-04` (year, hyphen, two-digit month). Month must be between 01 and 12.

**End month before start month:**
```
Error: End month cannot be before start month
```
- **Cause:** In `--date-range`, the end month is earlier than the start month
- **Solution:** Ensure the second date is on or after the first date (e.g., `--date-range 2081-04 2081-06`)

**No transactions found for period:**
```
Warning: No transactions found for <month>
```
- **Cause:** The database contains no data for the specified month(s)
- **Solution:** Verify the database is properly restored and contains data for the requested period. Check that the date range is correct and matches actual transaction data.

**Database connection failed:**
```
Error: Unable to connect to database
```
- **Cause:** Database configuration is incorrect or database is unavailable
- **Solution:** Verify `TARGET_DATABASE` setting, database connection string, and that SQL Server is running. Use `vat-cli test-db` to diagnose.

**No valid transactions after status filtering:**
```
Warning: No valid transactions after status filtering
```
- **Cause:** All transactions in the period have Status != '001-00'
- **Solution:** This is expected if no valid transactions exist for the period. Check source data to confirm.

### Debug Mode
Run any command with `--debug` flag for verbose logging:
```sh
vat-cli --debug run --fiscal-year 2081-82 --dry-run
```

### Dry-Run Mode
Test the workflow without making changes:
```sh
vat-cli run --fiscal-year 2081-82 --dry-run
```
This will:
- Skip database restore
- Skip file uploads to Google Drive
- Skip email sends
- Still create local Excel and HTML files for inspection

## Architecture Notes

### Single-Month vs. Consolidated Workflows
- **Single-Month (`--month`):** Uses IRD-provided Excel templates with pre-formatted sheets. Follows traditional monthly reporting structure.
- **Consolidated (`--fiscal-year`, `--date-range`):** Skips templates and generates generic consolidated purchase/sales files. Better for quarterly or annual analysis across months.

### Transaction Filtering Pipeline
The consolidation workflow applies filters in this order:
1. **Status Filter:** Keep only Status = '001-00' (valid transactions)
2. **Type Filter:** Separate into Purchase (Type 1) and Sales (Type 2)
3. **Aggregation:** Generate summary metrics for each period

This ensures only valid, non-canceled transactions are included in consolidated reports.

### Performance Considerations
- Large multi-month reports are processed using pandas DataFrames for efficiency
- Excel files are written directly to disk without loading entire files into memory
- Database queries are optimized for date ranges to minimize data transfer
- Consider using `--dry-run` for large date ranges to preview without file I/O

## License
MIT (c) Ashish Kandu

## Author
Ashish Kandu (<ashishkandu43@gmail.com>)
