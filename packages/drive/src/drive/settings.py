from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.config.repo import find_repo_root


class GoogleDriveSettings(BaseSettings):
    """Google Drive integration settings."""

    model_config = SettingsConfigDict(
        env_prefix="GDRIVE_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base paths
    repo_root: Path = find_repo_root(Path(__file__).resolve())

    # --- Settings for User Account (Download) ---
    # Path to the Google API client secrets file (for user authentication)
    CREDENTIALS_CLIENT_SECRETS: Path = Field(repo_root / "client_secrets.json")

    # --- OAuth token directory and account configuration ---
    # Directory where per-account OAuth tokens will be stored (token_{account}.json)
    OAUTH_TOKEN_DIR: Path = Field(repo_root / ".gdrive_tokens")

    # Optional default account aliases (simple strings or email addresses)
    DEFAULT_OAUTH_ACCOUNT: str | None = Field(None)
    # Optional explicit accounts for download/upload flows. If set, these override DEFAULT_OAUTH_ACCOUNT
    DOWNLOAD_OAUTH_ACCOUNT: str | None = Field(None)
    UPLOAD_OAUTH_ACCOUNT: str | None = Field(None)
