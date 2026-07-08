from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .repo import find_repo_root


class SharedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Base paths
    shared_package_path: Path = Path(__file__).resolve().parent.parent
    repo_root: Path = find_repo_root(shared_package_path)

    # Common paths for application data
    BACKUP_DIR: Path = repo_root / "data" / "backups"
    DEFAULT_DOWNLOAD_PATH: Path = repo_root / "data" / "downloads"
    DEFAULT_REPORTS_PATH: Path = repo_root / "data" / "reports"

    # Mount point for MSSQL backups (e.g., where a volume is mounted in Docker)
    MSSQL_BACKUP_MOUNT: Path = Field(
        "/var/opt/mssql/backups",
        description="Mount path for MSSQL backups inside the container. Same as defined in docker service.",
    )
    TARGET_DATABASE: str = Field(
        "VatBillingSoftware",
        description="Name of the target database for operations.",
    )

    # Company Information
    COMPANY_PAN: str = Field(..., description="The company's PAN.")
    COMPANY_OFFICE_NAME: str = Field(
        ...,
        description="The official name of the company.",
    )

    MSSQL_BACKUP_FILE_PATTERN: str = r"VatBillingSoftware_\d+_\d+\.bak"

    # Business Thresholds
    HIGH_VALUE_TRANSACTION_THRESHOLD: int = 1_00_000

    # The name of the base folder in Google Drive where reports will be uploaded.
    # This folder will contain subfolders for fiscal years, then months.
    GDRIVE_REPORTS_BASE_FOLDER_NAME: str = Field(
        "VAT Reports",
        description="Base folder name in Google Drive for uploaded reports.",
    )
    # Optional: The ID of the base Google Drive folder. If provided, speeds up lookups.
    # If not provided, the folder will be searched for by name or created.
    GDRIVE_REPORTS_BASE_FOLDER_ID: str | None = Field(
        None,
        description="Optional ID of the base Google Drive folder for reports. If not set, it will be discovered/created by name.",
    )

    # Page size for listing files from Google Drive (number of results per API call)
    GOOGLE_DRIVE_PAGE_SIZE: int = Field(
        10,
        description="The number of files to retrieve from Drive per API call when listing.",
    )

    # Default subject prefix for generated reports
    EMAIL_SUBJECT_PREFIX: str = Field(
        "VAT Report - ",
        description="Prefix for the email subject line",
    )

    def ensure_dirs(self):
        """Ensures all necessary application directories exist."""
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.DEFAULT_DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
        self.DEFAULT_REPORTS_PATH.mkdir(parents=True, exist_ok=True)
