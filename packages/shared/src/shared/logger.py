import logging
import logging.config
import sys

try:
    from rich.console import Console
    from rich.logging import RichHandler  # noqa: F401

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from shared.config import LoggingConfig as _LoggingConfig


class LoggerFactory:
    """
    Reusable logger factory responsible for centralizing logging configuration.

    It ensures the logging system is configured only once and provides named loggers.
    """

    # _is_configured = False  <-- REMOVE THIS FLAG. It prevents reconfiguration.

    @staticmethod
    def _get_base_logging_config(*, debug_mode: bool) -> dict:
        """
        Constructs the base logging configuration dictionary.

        Determines handlers, formatters, and logger levels based on debug_mode
        and Rich library availability.
        """
        cfg = _LoggingConfig()

        root_level_str = "DEBUG" if debug_mode else cfg.LOG_LEVEL.upper()

        basic_formatter = {
            "format": "[%(levelname)s]: %(asctime)s - (%(name)s) %(message)s",
            "datefmt": "[%X]",
        }

        console_handler_config = {
            "level": root_level_str,
            "formatter": "basic",
        }

        if RICH_AVAILABLE:
            console_handler_config.update(
                {
                    "class": "rich.logging.RichHandler",
                    "markup": True,
                    "rich_tracebacks": True,
                    "show_time": False,
                    "show_level": False,
                    "show_path": False,
                    "console": Console(file=sys.stderr),
                },
            )
        else:
            console_handler_config.update(
                {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            )

        file_handler_config = {
            "class": "logging.FileHandler",
            "level": root_level_str,
            "formatter": "file",
            "filename": str(cfg.LOG_FILE_PATH),
            "mode": "a",
        }

        noisy_loggers_config = (
            {
                "sqlalchemy.engine.Engine": {"level": "WARNING", "propagate": True},
                "urllib3.connectionpool": {"level": "WARNING", "propagate": True},
                "requests.packages.urllib3.connectionpool": {
                    "level": "WARNING",
                    "propagate": True,
                },
            }
            if not debug_mode
            else {}
        )

        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "basic": basic_formatter,
                "file": {
                    "format": "[%(levelname)s]: %(asctime)s - (%(name)s) %(message)s",
                },
            },
            "handlers": {
                "console": console_handler_config,
                "filehandler": file_handler_config,
            },
            "root": {
                "level": root_level_str,
                "handlers": ["console", "filehandler"],
            },
            "loggers": noisy_loggers_config,  # Apply noisy logger configurations
        }

    @staticmethod
    def configure_logging(*, debug_mode: bool = False) -> None:
        """
        Configures the Python logging system globally based on debug_mode.

        This method should be called once at application startup.
        It safely reconfigures the root logger and ensures consistency.
        """
        # Always remove existing handlers from the root logger before applying new config
        # This prevents duplicate output if called multiple times.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            if hasattr(handler, "close"):  # Ensure handlers are properly closed
                handler.close()

        logging.root.manager.loggerDict.clear()  # This is the key fix for early loggers

        log_config = LoggerFactory._get_base_logging_config(debug_mode=debug_mode)
        logging.config.dictConfig(log_config)

        # Log the configuration message. This message will only appear if
        # debug_mode is True, as the logger's level will be set.
        logging.getLogger(__name__).debug(
            "Logging system configured by LoggerFactory in DEBUG mode.",
        )

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Retrieves a logger instance. It assumes configure_logging will be called at application startup to set up the global logging configuration."""
        return logging.getLogger(name)
