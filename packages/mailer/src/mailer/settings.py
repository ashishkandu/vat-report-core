from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailSettings(BaseSettings):
    """Settings for sending emails."""

    SMTP_HOST: str = Field(
        "smtp.gmail.com",
        description="SMTP server hostname (e.g., smtp.gmail.com)",
    )
    SMTP_PORT: int = Field(
        587,
        description="SMTP server port (e.g., 587 for TLS, 465 for SSL)",
    )
    SMTP_USERNAME: str = Field(
        ...,
        description="Username for SMTP authentication (sender email address)",
    )
    SMTP_PASSWORD: str = Field(
        ...,
        description="Password for SMTP authentication (or app-specific password)",
    )
    SMTP_USE_TLS: bool = Field(
        True,
        description="Whether to use TLS encryption (recommended for port 587)",
    )
    SMTP_USE_SSL: bool = Field(
        False,
        description="Whether to use SSL encryption (for port 465, mutually exclusive with TLS)",
    )

    # Sender email address (should match SMTP_USERNAME in most cases)
    SENDER: str = Field(
        ...,
        description="The 'From' email address",
    )
    # List of recipient email addresses
    RECIPIENTS: list[str] = Field(
        ...,
        description="Comma-separated list of recipient email addresses",
    )

    model_config = SettingsConfigDict(
        env_prefix="EMAIL_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
