from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseSettings):
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO")
    LOG_FILE_PATH: Path = Field("logs.log")

    # Future use
    LOG_FILE_MAX_BYTES: int = Field(10 * 1024 * 1024)  # 10 MB
    LOG_FILE_BACKUP_COUNT: int = Field(5)
    LOG_FORMAT: str = Field(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def model_post_init(self, __context):  # noqa: PYI063
        # Ensure the log directory exists
        log_dir = self.LOG_FILE_PATH.parent
        if log_dir and str(log_dir) != ".":
            log_dir.mkdir(parents=True, exist_ok=True)
