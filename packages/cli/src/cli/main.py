import logging
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import click
from dbkit.engine import get_engine
from downloader.manager import download_ird_templates
from file_operations.backup_rotator import (
    rotate_backups as rotate_backups_func,
)
from file_operations.disk_writer import write_bytes_to_disk
from nepalidates import FilingMonth
from reporting.fetcher import fetch_raw_transaction_dataframe
from reporting.fiscal_year import FiscalYearRange
from reporting.formatter.console_formatter import ConsoleReportFormatter
from reporting.formatter.html_formatter import HtmlReportFormatter
from reporting.models import CompanyInfo
from reporting.processor import (
    LakhTransactionsReport,
    PurchaseReport,
    SalesReport,
    generate_summary_analytics,
)
from restorer.restore import restore_database
from rich.console import Console
from shared import SharedSettings
from shared.constants import CommonReportType
from shared.logger import LoggerFactory
from shared.utils import get_company_info_from_args_or_settings

# Import the main workflow orchestrator
from vat_report.workflow import execute_report_generation_workflow, execute_vat_workflow

from .params import FILING_MONTH_SELECTOR

console = Console()

# This prevents logging.basicConfig() from running implicitly if any getLogger() call
# happens before LoggerFactory.configure_logging is executed.
logging.getLogger().addHandler(logging.NullHandler())


class CLIContext:
    def __init__(self):
        self.logger: logging.Logger = None
        self.settings: SharedSettings = None


@click.group()
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging for more verbose output.",
)
@click.pass_context
def cli(ctx: click.Context, *, debug: bool):
    """VAT Reporting Command Line Interface."""
    # Initialize the custom context object and store it in Click's context
    ctx.obj = CLIContext()

    LoggerFactory.configure_logging(debug_mode=debug)

    ctx.obj.logger = LoggerFactory.get_logger("vat-cli")

    ctx.obj.settings = SharedSettings()

    ctx.obj.settings.ensure_dirs()

    ctx.obj.logger.debug(
        "CLI application initialized and logging configured via LoggerFactory.",
    )


def filing_month_options(func):
    """Decorator to apply common filing month options and enforce mutual exclusivity."""

    @click.option(
        "--month",
        "-m",
        "filing_month_str",
        type=str,
        help="Filing month in BSYYYY-MM format (e.g., 2081-02).",
        default=None,
    )
    @click.option(
        "--fiscal-year",
        "-f",
        "fiscal_year_str",
        type=str,
        help="Generate report for entire fiscal year (e.g., 2080-81)",
        default=None,
    )
    @click.option(
        "--date-range",
        "-d",
        nargs=2,
        help="Generate report for custom date range (e.g., '2080-04 2081-03')",
        type=str,
    )
    @click.option(
        "--select-month",
        "-s",
        "selected_filing_month_value",
        type=FILING_MONTH_SELECTOR,
        is_flag=False,
        flag_value="__prompt__",
        default=None,
        help="Interactively select a filing month from a list. If provided without a value, it will prompt for selection. You can also pass 'current', 'previous', a list number, or BSYYYY-MM.",
    )
    @click.option(
        "--current",
        "use_current",
        is_flag=True,
        help="Use the current filing month.",
    )
    @click.option(
        "--previous",
        "use_previous",
        is_flag=True,
        help="Use the previous filing month.",
    )
    @click.pass_context
    def wrapper(
        ctx: click.Context,
        filing_month_str: str | None,
        fiscal_year_str: str | None,
        date_range: tuple[str, str] | None,
        selected_filing_month_value: Any,
        *args,
        use_current: bool,
        use_previous: bool,
        **kwargs,
    ):
        from reporting.fiscal_year import FiscalYearRange

        logger = ctx.obj.logger

        options_provided = sum(
            [
                filing_month_str is not None,
                fiscal_year_str is not None,
                date_range is not None,
                selected_filing_month_value is not None,
                use_current,
                use_previous,
            ],
        )

        if options_provided > 1:
            ctx.fail(
                "Error: Only one of --month, --fiscal-year, --date-range, --select-month, --current, or --previous can be specified.",
            )

        # Handle fiscal year option
        if fiscal_year_str:
            try:
                fiscal_range = FiscalYearRange.from_fiscal_year(fiscal_year_str)
                return func(ctx, fiscal_range, *args, **kwargs)
            except ValueError as e:
                ctx.fail(f"Error with --fiscal-year format: {e}")

        # Handle date range option
        if date_range:
            try:
                fiscal_range = FiscalYearRange.from_date_range(*date_range)
                return func(ctx, fiscal_range, *args, **kwargs)
            except ValueError as e:
                ctx.fail(f"Error with --date-range format: {e}")

        # Handle single month options
        final_filing_month_obj = None

        if selected_filing_month_value == "__prompt__":
            final_filing_month_obj = FILING_MONTH_SELECTOR.prompt_for_value(
                ctx.command.params,
                ctx,
            )
        elif selected_filing_month_value:
            final_filing_month_obj = selected_filing_month_value
        elif use_current:
            final_filing_month_obj = FilingMonth.current()
        elif use_previous:
            final_filing_month_obj = FilingMonth.previous()
        elif filing_month_str:
            try:
                final_filing_month_obj = FilingMonth.from_string(filing_month_str)
            except ValueError as e:
                ctx.fail(f"Error with --month format: {e}")

        if final_filing_month_obj is None:
            final_filing_month_obj = FilingMonth.previous()
            logger.info(
                "No filing month option provided. Defaulting to previous month: %s.",
                final_filing_month_obj,
            )

        # For single month, create a fiscal range with same start and end
        fiscal_range = FiscalYearRange(
            start_month=final_filing_month_obj, end_month=final_filing_month_obj
        )
        return func(ctx, fiscal_range, *args, **kwargs)

    return wrapper


@cli.command(
    "run",
    help="Run the full VAT reporting workflow for a month, fiscal year, or date range.",
)
@click.option(
    "--pan",
    "-p",
    help="Override the PAN number from settings. Useful for multi-company setups.",
)
@click.option(
    "--office-name",
    "-o",
    help="Override the office name from settings. Useful for multi-company setups.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate the workflow without making permanent changes (e.g., no DB restore, no file uploads, no emails).",
)
@click.option(
    "--output-analytics-to-console/--no-output-analytics-to-console",
    default=True,
    help="Output analytics summary to console (default: True).",
)
@click.option(
    "--save-analytics-html-locally/--no-save-analytics-html-locally",
    default=True,
    help="Save analytics HTML report locally (default: True).",
)
@click.option(
    "--upload-to-gdrive",
    is_flag=True,
    help="Upload generated reports and backups to Google Drive. Requires Google Drive API setup.",
)
@click.option(
    "--send-email",
    is_flag=True,
    help="Send an email with reports. Requires SMTP email configuration.",
)
@click.option(
    "--save-excel-locally/--no-save-excel-locally",
    default=True,
    help="Save generated Excel reports locally (default: True).",
)
@filing_month_options
def run_command(  # noqa: PLR0913
    ctx: click.Context,
    fiscal_range: FiscalYearRange,
    pan: str | None,
    office_name: str | None,
    *,
    dry_run: bool,
    output_analytics_to_console: bool,
    save_analytics_html_locally: bool,
    upload_to_gdrive: bool,
    send_email: bool,
    save_excel_locally: bool,
):
    """Run the full VAT reporting workflow."""
    from vat_report.fiscal_year_workflow import execute_fiscal_year_workflow

    logger = ctx.obj.logger
    settings = ctx.obj.settings

    try:
        console.print(
            f"[bold green]Starting VAT Report Workflow for period {fiscal_range.start_month.name} to {fiscal_range.end_month.name}...[/bold green]"
        )

        # For single month, use original workflow
        if fiscal_range.start_month == fiscal_range.end_month:
            execute_vat_workflow(
                filing_month=fiscal_range.start_month,
                pan=pan,
                office_name=office_name,
                dry_run=dry_run,
                output_analytics_to_console=output_analytics_to_console,
                save_analytics_html_locally=save_analytics_html_locally,
                upload_to_gdrive=upload_to_gdrive,
                send_email=send_email,
                save_excel_locally=save_excel_locally,
            )
        else:
            # For fiscal year or date range, use new workflow
            execute_fiscal_year_workflow(
                fiscal_range=fiscal_range,
                settings=settings,
                dry_run=dry_run,
                output_analytics_to_console=output_analytics_to_console,
                save_analytics_html_locally=save_analytics_html_locally,
                upload_to_gdrive=upload_to_gdrive,
                send_email=send_email,
                save_excel_locally=save_excel_locally,
            )

        console.print("[bold green]VAT Report Workflow Completed![/bold green]")
    except Exception as e:
        logger.exception(
            "An error occurred during the VAT report workflow execution.",
        )
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("analytics", help="Generate and print summary analytics for a month.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["console", "html"]),
    default="console",
    help="Output format.",
)
@filing_month_options
def analytics_command(
    ctx: click.Context,
    filing_month_obj: FilingMonth,
    output_format: str,
):
    """
    Generate and print summary analytics for a month.

    Does not run the full workflow (e.g., no DB restore).
    """
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.info("--- Starting Analytics Generation via CLI ---")
    try:
        engine = get_engine(settings.TARGET_DATABASE)

        raw_transactions_df = fetch_raw_transaction_dataframe(
            engine,
            filing_month_obj.ad_date_range.start,
            filing_month_obj.ad_date_range.end,
        )

        if raw_transactions_df.empty:
            console.print(
                "[bold yellow]No raw transactions found for the specified month. Cannot generate analytics.[/bold yellow]",
            )
            logger.warning(
                "No transaction data found for %s. Analytics not generated.",
                filing_month_obj.name,
            )
            sys.exit(0)

        analytics_summary_data = generate_summary_analytics(raw_transactions_df)

        if output_format == "console":
            console_formatter = ConsoleReportFormatter(
                summary_data=analytics_summary_data,
                filing_month_name=filing_month_obj.name,
            )
            console_output = console_formatter.format_report()
            console.print(console_output)
        else:  # html output_format
            html_formatter = HtmlReportFormatter(
                summary_data=analytics_summary_data,
                filing_month_name=filing_month_obj.name,
            )
            html_content = html_formatter.format_report()

            html_filename = f"summary_analytics_{filing_month_obj.name}.html"
            html_report_filepath = (
                settings.DEFAULT_REPORTS_PATH  # Use DEFAULT_REPORTS_PATH from settings
                / filing_month_obj.fiscal_year.replace("/", "-")
                / filing_month_obj.name
                / html_filename
            )
            write_bytes_to_disk(
                BytesIO(html_content.encode("utf-8")),
                html_report_filepath,
            )
            console.print(
                f"[bold green]HTML analytics report saved to:[/bold green] [cyan]{html_report_filepath}[/cyan]",
            )
    except Exception as e:
        logger.exception("An error occurred in the analytics command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("export-report", help="Export a specific report type to Excel.")
@click.option(
    "--type",
    "-t",
    "report_type_str",
    required=True,
    type=click.Choice(["purchase", "sales", "lakh-transactions"]),
    help="Report type.",
)
@click.option("--pan", "-p", type=str, help="Company PAN (overrides config).")
@click.option(
    "--office-name",
    "-o",
    type=str,
    help="Company office name (overrides config).",
)
@filing_month_options
def export_report(
    ctx: click.Context,
    filing_month_obj: FilingMonth,
    report_type_str: str,
    pan: str | None,
    office_name: str | None,
):
    """Export a specific report type to Excel."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.debug("--- Starting Export for %s Report ---", report_type_str.upper())
    try:
        console.print(
            f"[bold green]Exporting {report_type_str} report for {filing_month_obj.name}...[/bold green]",
        )
        company_info_dto = get_company_info_from_args_or_settings(
            pan=pan,
            office_name=office_name,
            settings=settings,
            logger_instance=logger,
        )

        engine = get_engine(settings.TARGET_DATABASE)
        raw_transactions_df = fetch_raw_transaction_dataframe(
            engine,
            filing_month_obj.ad_date_range.start,
            filing_month_obj.ad_date_range.end,
        )

        if raw_transactions_df.empty:
            console.print(
                f"[bold yellow]No transaction data found for {filing_month_obj.name}. Skipping report export.[/bold yellow]",
            )
            logger.warning(
                "No transaction data found for %s. Report export not performed.",
                filing_month_obj.name,
            )
            sys.exit(0)

        report_type_enum = {
            "purchase": CommonReportType.PURCHASE,
            "sales": CommonReportType.SALES,
            "lakh-transactions": CommonReportType.LAKH_TRANSACTIONS,
        }[report_type_str]

        downloaded_templates = download_ird_templates(
            template_types=[report_type_enum],
            save_locally=False,
            local_save_dir=settings.DEFAULT_DOWNLOAD_PATH,
        )

        report_instance = None
        if report_type_enum == CommonReportType.PURCHASE:
            report_instance = PurchaseReport(
                filing_month=filing_month_obj,
                company_info=company_info_dto,
            )
        elif report_type_enum == CommonReportType.SALES:
            report_instance = SalesReport(
                filing_month=filing_month_obj,
                company_info=company_info_dto,
            )
        elif report_type_enum == CommonReportType.LAKH_TRANSACTIONS:
            report_instance = LakhTransactionsReport(
                filing_month=filing_month_obj,
                company_info=company_info_dto,
            )

        if report_instance:
            report_instance.process_raw_data(raw_transactions_df)
            if report_instance.processed_dataframe.empty:
                console.print(
                    f"[bold yellow]{report_type_str.capitalize()} report DataFrame is empty, skipping export.[/bold yellow]",
                )
                sys.exit(0)

            template_buffer = downloaded_templates.get(report_type_enum)

            if not template_buffer:
                console.print(
                    f"[bold red]Failed to download template for {report_type_str} report. Cannot export.[/bold red]",
                )
                sys.exit(1)

            exported_excel_buffer = report_instance.export_to_excel(
                template_buffer=template_buffer,
            )

            output_filepath = (
                settings.DEFAULT_REPORTS_PATH
                / filing_month_obj.fiscal_year.replace("/", "-")
                / filing_month_obj.name
                / f"{report_type_enum.name} - {filing_month_obj.name}{report_type_enum.file_extension}"
            )
            write_bytes_to_disk(exported_excel_buffer, output_filepath)
            console.print(
                f"[bold green]{report_type_str.capitalize()} Report exported to:[/bold green] [cyan]{output_filepath.resolve()}[/cyan]",
            )
        else:
            console.print(
                f"[bold red]Invalid report type: {report_type_str}[/bold red]",
            )
            sys.exit(1)

    except Exception as e:
        logger.exception(
            "An error occurred in the export-report command for type %s.",
            report_type_str,
        )
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("download-templates")
@click.option(
    "--type",
    "-t",
    "template_type_str",
    type=click.Choice(["purchase", "sales", "lakh-transactions"]),
    help="Specific template type to download. If not specified, all types will be downloaded.",
)
@click.pass_context
def download_templates(ctx: click.Context, template_type_str: str | None):
    """Download IRD Excel templates."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    try:
        type_map = {
            "purchase": CommonReportType.PURCHASE,
            "sales": CommonReportType.SALES,
            "lakh-transactions": CommonReportType.LAKH_TRANSACTIONS,
        }

        template_types_to_download = []
        if template_type_str:
            template_types_to_download = [type_map[template_type_str]]
        else:
            template_types_to_download = list(type_map.values())

        download_ird_templates(
            template_types=template_types_to_download,
            save_locally=True,  # This command always saves locally
            local_save_dir=settings.DEFAULT_DOWNLOAD_PATH,
        )
        console.print(
            f"Saved locally to: [cyan]{settings.DEFAULT_DOWNLOAD_PATH.resolve()}[/cyan]",
        )

    except Exception as e:
        logger.exception("An error occurred in the download-templates command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("rotate-backups")
@click.pass_context
def rotate_backups(ctx: click.Context):
    """Rotates old database backups based on retention policy."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.info("--- Starting Backup Rotation ---")
    try:
        deleted_count, errors = rotate_backups_func(settings.BACKUP_DIR)

        if errors:
            console.print(
                f"[bold yellow]Backups rotated with errors.[/bold yellow] Deleted: [bold green]{deleted_count}[/bold green], Errors: [bold red]{len(errors)}[/bold red].",
            )
            for error_msg in errors:
                logger.error("Backup rotation error: %s", error_msg)
        else:
            console.print(
                f"[bold green]Backups rotated successfully.[/bold green] Deleted [bold green]{deleted_count}[/bold green] old backups.",
            )
    except Exception as e:
        logger.exception("An error occurred in the rotate-backups command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("restore-db")
@click.option(
    "--file",
    "-f",
    "backup_file_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the .bak backup file to restore from.",
)
@click.pass_context
def restore_db(ctx: click.Context, backup_file_path: Path):
    """Restores the database from a specified backup file."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.info("--- Starting Database Restore from %s ---", backup_file_path.name)
    try:
        # Create path inside docker container
        mssql_backup_path = (
            settings.MSSQL_BACKUP_MOUNT / backup_file_path.name
        )  # Use MSSQL_BACKUP_MOUNT from settings
        restore_database(
            backup_file=mssql_backup_path,
            target_db=settings.TARGET_DATABASE,
        )
        console.print(
            f"[bold green]Database restored from:[/bold green] [cyan]{backup_file_path}[/cyan]",
        )
    except Exception as e:
        logger.exception("An error occurred in the restore-db command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(
    "filing-month",
    help="Show details about a specific filing month, including BS and AD date ranges and fiscal year.",
)
@filing_month_options
def filing_month_command(
    ctx: click.Context,
    filing_month_obj: FilingMonth,
):
    """Show details about a filing month."""
    logger = ctx.obj.logger
    try:
        fm = filing_month_obj
        console.print(f"[bold]Filing Month:[/bold] {fm.name}")
        console.print(
            f"[bold]BS Range:[/bold] {fm.bs_date_range.start} to {fm.bs_date_range.end}",
        )
        console.print(
            f"[bold]AD Range:[/bold] {fm.ad_date_range.start} to {fm.ad_date_range.end}",
        )
        console.print(f"[bold]Fiscal Year:[/bold] {fm.fiscal_year}")
        console.print(f"[bold]Nepali Name:[/bold] {fm.name}")
    except ValueError as e:
        logger.exception("Invalid filing month input")
        console.print(f"[bold red]Error: Invalid month format or value:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("An error occurred in the filing-month command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx: click.Context):
    """Print current application configuration."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    try:
        config_json = settings.model_dump_json(indent=2)
        console.print(f"[bold green]Current Configuration:[/bold green]\n{config_json}")
    except Exception as e:
        logger.exception("An error occurred in the config command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command(
    "drive-auth",
    help="Run interactive OAuth flow and persist token for a named account.",
)
@click.option(
    "--account",
    "account",
    required=False,
    type=str,
    help="Account alias or email to name the token file (e.g., 'upload' or 'user@example.com').",
)
@click.pass_context
def drive_auth(ctx: click.Context, account: str | None):
    """Interactive helper to create/persist an OAuth token for a given account.

    This will run the installed app flow and write token_{account}.json under the
    configured GDRIVE_OAUTH_TOKEN_DIR.
    """
    logger = ctx.obj.logger
    try:
        # Import here to avoid pulling Google libs unless needed
        from drive.auth import get_oauth_drive_service

        logger.info("Starting interactive Drive OAuth flow for account=%s", account)
        service = get_oauth_drive_service(account=account)
        if service:
            console.print(
                f"[bold green]OAuth token created/persisted for account: {account or 'default'}[/bold green]"
            )
    except Exception as e:
        logger.exception("Drive OAuth flow failed for account=%s", account)
        console.print(f"[bold red]Error during drive-auth:[/bold red] {e}")
        sys.exit(1)


@cli.command("test-db")
@click.pass_context
def test_db(ctx: click.Context):
    """Tests the connection to the configured database."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.info("--- Testing Database Connection ---")
    try:
        engine = get_engine(settings.TARGET_DATABASE)
        with engine.connect():
            pass
        console.print("[bold green]Database connection successful![/bold green]")
    except Exception as e:  # noqa: BLE001
        logger.error("Database connection failed.")  # noqa: TRY400
        console.print(f"[bold red]Database connection failed:[/bold red] {e}")
        sys.exit(1)


@cli.command("shell")
@click.pass_context
def shell_command(ctx: click.Context):
    """Starts an interactive Python shell with pre-imported project context."""
    logger = ctx.obj.logger
    settings = ctx.obj.settings
    logger.info("--- Starting Interactive Shell ---")
    try:
        import code

        import pandas as pd

        local_ctx = {
            "settings": settings,
            "logger": logger,
            "pd": pd,
            "FilingMonth": FilingMonth,
            "CompanyInfo": CompanyInfo,
            "CommonReportType": CommonReportType,
            "get_engine": get_engine,
        }
        banner = (
            "VAT CLI Interactive Shell.\n"
            "Pre-imported objects: settings, logger, pd, FilingMonth, CompanyInfo, CommonReportType, get_engine."
            "\nType 'exit()' to quit."
        )
        try:
            from IPython import embed

            embed(banner1=banner, user_ns=local_ctx)
        except ImportError:
            console.print(
                "[yellow]IPython not found. Falling back to standard Python shell.[/yellow]",
            )
            code.interact(banner=banner, local=local_ctx)
    except RuntimeError as e:
        logger.exception("A runtime error occurred in the 'shell' command.")
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("[bold yellow]Shell interrupted by user.[/bold yellow]")
        sys.exit(0)


@cli.command(
    "generate-reports",
    help="Generate VAT reports and analytics for a selected month, assuming DB is ready. "
    "Optionally email and upload to Google Drive.",
)
@click.option(
    "--pan",
    "-p",
    help="Override the PAN number from settings. Useful for multi-company setups.",
)
@click.option(
    "--office-name",
    "-o",
    help="Override the office name from settings. Useful for multi-company setups.",
)
@click.option(
    "--output-analytics-to-console/--no-output-analytics-to-console",
    default=True,
    help="Output analytics summary to console (default: True).",
)
@click.option(
    "--save-analytics-html-locally/--no-save-analytics-html-locally",
    default=True,
    help="Save analytics HTML report locally (default: True).",
)
@click.option(
    "--upload-to-gdrive",
    is_flag=True,
    help="Upload generated reports and analytics to Google Drive. Requires Google Drive API setup.",
)
@click.option(
    "--send-email",
    is_flag=True,
    help="Send an email with reports. Requires SMTP email configuration.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate report generation, email, and upload without making permanent changes.",
)
@click.option(
    "--save-excel-locally/--no-save-excel-locally",
    default=True,
    help="Save generated Excel reports locally (default: True).",
)
@filing_month_options
def generate_reports_command(  # noqa: PLR0913
    ctx: click.Context,
    filing_month_obj: FilingMonth,
    pan: str | None,
    office_name: str | None,
    *,
    output_analytics_to_console: bool,
    save_analytics_html_locally: bool,
    upload_to_gdrive: bool,
    send_email: bool,
    dry_run: bool,
    save_excel_locally: bool,
):
    """
    Generate VAT reports and analytics for a selected month, assuming DB is ready.

    Optionally email and upload to Google Drive.
    """
    logger = ctx.obj.logger  # Get logger from context for consistent logging

    try:
        console.print(
            f"[bold green]Starting Report Generation Workflow for {filing_month_obj.name} (Dry Run: {dry_run})...[/bold green]",
        )
        execute_report_generation_workflow(
            filing_month=filing_month_obj,
            pan=pan,
            office_name=office_name,
            dry_run=dry_run,
            output_analytics_to_console=output_analytics_to_console,
            save_analytics_html_locally=save_analytics_html_locally,
            upload_to_gdrive=upload_to_gdrive,
            send_email=send_email,
            save_excel_locally=save_excel_locally,
        )
        console.print("[bold green]Report Generation Workflow Completed![/bold green]")
    except Exception as e:
        logger.exception(
            "An error occurred during the report generation workflow execution.",
        )
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
