import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from shared.logger import LoggerFactory

from .settings import GoogleDriveSettings

logger = LoggerFactory.get_logger(__name__)
settings = GoogleDriveSettings()

# Define the scope for Google Drive API
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/docs",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def get_oauth_drive_service(account: str | None = None) -> Resource:
    """Get a Drive resource using per-account OAuth tokens.

    If `account` is provided, resolves token to
    settings.OAUTH_TOKEN_DIR / f"token_{account}.json".
    """
    # Ensure client secrets exists
    if not settings.CREDENTIALS_CLIENT_SECRETS.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {settings.CREDENTIALS_CLIENT_SECRETS}"
        )

    # Resolve token path
    if account:
        safe_account = account.replace("@", "_at_").replace("/", "_")
        token_path = settings.OAUTH_TOKEN_DIR / f"token_{safe_account}.json"
    else:
        token_path = settings.OAUTH_TOKEN_DIR / "token.json"

    # Ensure token directory exists (callers will check if token file exists)
    settings.OAUTH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            logger.exception(
                "Invalid token file at %s. Will attempt interactive auth.", token_path
            )

    # Attempt refresh if possible
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # persist refreshed token
                try:
                    settings.OAUTH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
                    with token_path.open("w") as f:
                        f.write(creds.to_json())
                except Exception:
                    logger.exception(
                        "Failed to persist refreshed token to %s", token_path
                    )
            except RefreshError:
                logger.exception(
                    "Error refreshing credentials for %s. Will request new credentials.",
                    token_path,
                )
                creds = None

    # If still no valid creds, do interactive flow (local dev). CI should pre-provide token file.
    if not creds or not creds.valid:
        # Detect non-interactive environment: CI/GitHub Actions or no TTY
        is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
        try:
            is_tty = os.isatty(0)
        except (OSError, ValueError):
            is_tty = False

        if is_ci or not is_tty:
            raise RuntimeError(
                f"No valid OAuth token available for account={account} and running non-interactively. "
                f"Place a token file at {token_path} with offline refresh_token."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.CREDENTIALS_CLIENT_SECRETS), SCOPES
        )
        creds = flow.run_local_server(port=0)

        try:
            settings.OAUTH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
            with token_path.open("w") as token_file:
                token_file.write(creds.to_json())
        except Exception:
            logger.exception("Failed to persist new token to %s", token_path)

    try:
        service = build("drive", "v3", credentials=creds)
        logger.info("Google Drive service built successfully for account=%s", account)
    except Exception as e:
        logger.exception("Error building Google Drive service for account=%s", account)
        raise RuntimeError(f"Could not build Google Drive service: {e}") from e

    return service


def get_drive_service() -> Resource:
    """Backward-compatible wrapper that uses default token path."""
    return get_oauth_drive_service(None)


# Service account support removed. Use get_oauth_drive_service(account) instead.
