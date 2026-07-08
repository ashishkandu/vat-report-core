import click
from nepalidates.filing_month import FilingMonth
from shared.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class FilingMonthChoice(click.ParamType):
    """
    A custom Click parameter type for selecting a FilingMonth from a dynamic list.

    If the input is not a choice, it falls back to parsing as 'BSYYYY-MM'.
    """

    name = "filing_month_choice"

    def __init__(self, num_previous_months: int = 12):
        super().__init__()
        self.num_previous_months = num_previous_months
        self._choices: list[FilingMonth] | None = None
        self._choice_strings: list[str] | None = None

    def _generate_choices(self) -> None:
        """Generates the list of FilingMonth choices."""
        try:
            # Generate a range of months for selection, e.g., last 12 months
            # The get_filing_month_range handles limiting to current month/year
            self._choices = FilingMonth.get_filing_month_range(
                num_previous=self.num_previous_months,
            )
            # Create user-friendly strings for the prompt
            self._choice_strings = [str(fm) for fm in self._choices]
            logger.debug("Generated FilingMonth choices: %s", self._choice_strings)
        except Exception:
            logger.exception("Failed to generate FilingMonth choices.")
            self._choices = []
            self._choice_strings = []  # Fallback to empty if generation fails

    def get_metavar(
        self,
        param: click.Parameter,  # noqa: ARG002
        ctx: click.Context | None = None,  # noqa: ARG002
    ) -> str:
        """
        Returns the metavar for the parameter type.

        Accepts 'ctx' to be compatible with Click's internal calls.
        """
        # The 'ctx' parameter is now accepted, even if not strictly used for this simple metavar.
        return "[BSYYYY-MM|SELECT]"

    def convert(
        self,
        value: str,
        param: click.Parameter,
        ctx: click.Context,
    ):
        """
        Converts the input string value to a FilingMonth object.

        Supports 'current', 'previous', an index from the selector, or 'BSYYYY-MM'.
        """
        # Check if the value is '__prompt__' and trigger the prompt
        if value == "__prompt__":
            return self.prompt_for_value(param, ctx)

        self._generate_choices()  # Ensure choices are generated before conversion

        if value.lower() == "current" or value.lower() == "c":
            return FilingMonth.current()
        if value.lower() == "previous" or value.lower() == "p":
            return FilingMonth.previous()

        # Try to convert as an index from the generated choices
        if self._choice_strings:
            for idx, choice_str in enumerate(self._choice_strings):
                if value == str(idx + 1) or value.lower() == choice_str.lower():
                    return self._choices[idx]

        # Fallback to direct BSYYYY-MM parsing
        try:
            year_bs, month_num = map(int, value.split("-"))
            fm = FilingMonth(year=year_bs, month=month_num)
            logger.debug("Parsed filing month from string: %s", fm)
        except ValueError:
            self.fail(
                f"Invalid filing month: '{value}'. Expected a number from the list, 'current', 'previous', or BSYYYY-MM format (e.g., '2081-02').",
                param,
                ctx,
            )
        except Exception as e:  # noqa: BLE001
            self.fail(f"Error parsing filing month '{value}': {e}", param, ctx)
        else:
            return fm

    def prompt_for_value(
        self,
        param: click.Parameter,
        ctx: click.Context,
    ) -> FilingMonth:
        """Prompts the user to select a FilingMonth from a list."""
        self._generate_choices()  # Re-generate choices before prompting

        if not self._choices:
            logger.warning(
                "No FilingMonth choices available for selection. Prompting for manual input.",
            )
            return super().prompt_for_value(
                param,
                ctx,
            )  # Fallback to default Click prompt

        while True:
            click.echo("\n--- Select a Filing Month ---")
            for idx, fm_str in enumerate(self._choice_strings):
                click.echo(f"  {idx + 1}. {fm_str}")
            click.echo("---------------------------")
            click.echo("  c. Current Month")
            click.echo("  p. Previous Month")
            click.echo("  Or enter BSYYYY-MM (e.g., 2081-02)")
            value = click.prompt("Enter your choice (number, c, p, or BSYYYY-MM)")

            try:
                # Use the convert method to handle all parsing logic
                return self.convert(value, param, ctx)
            except click.exceptions.BadParameter as e:
                click.echo(f"Error: {e.message}")
            except ValueError as e:  # Catch ValueError from FilingMonth.__init__
                click.echo(f"Error: {e}")
            except Exception:
                logger.exception("Unexpected error during month selection.")
                click.echo("An unexpected error occurred. Please try again.")


# Instantiate the custom type for reuse
FILING_MONTH_SELECTOR = FilingMonthChoice()
