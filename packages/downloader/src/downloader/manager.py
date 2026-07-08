import logging
from io import BytesIO
from pathlib import Path

# Import Google Drive client and auth
from drive.auth import get_oauth_drive_service
from drive.client import GDriveClient
from drive.settings import GoogleDriveSettings
from file_operations.disk_writer import write_bytes_to_disk

# Import client packages
from ird_client.cbms import CBMSClient
from ird_client.taxpayer import TaxpayerClient
from shared import SharedSettings
from shared.constants import CommonReportType

logger = logging.getLogger(__name__)
settings = SharedSettings()
drive_settings = GoogleDriveSettings()


def _prepare_local_save_dir(
    *,
    save_locally: bool,
    local_save_dir: Path | None,
) -> Path | None:
    """Helper function to validate and prepare the local directory for saving files."""
    if not save_locally:
        return None

    if local_save_dir is None:
        local_save_dir = settings.DEFAULT_DOWNLOAD_PATH
        logger.info(
            "No local_save_dir provided. Defaulting to '%s'",
            local_save_dir.resolve(),
        )

    if not isinstance(local_save_dir, Path):
        local_save_dir = Path(local_save_dir)

    try:
        local_save_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Files will be saved locally to: %s", local_save_dir.resolve())
    except OSError as e:
        logger.exception("Failed to create local save directory '%s'", local_save_dir)
        msg = f"Invalid local_save_dir: Failed to create '{local_save_dir}'"
        raise ValueError(msg) from e
    return local_save_dir


def download_ird_templates(
    template_types: list[CommonReportType],
    *,
    save_locally: bool = False,
    local_save_dir: Path | None = None,
) -> dict[CommonReportType, BytesIO | None]:
    """
    Downloads specified IRD template files from CBMS and Taxpayer portals.

    Args:
        template_types (list[CommonReportType]): A list of specific template types (enum members) to download.
                                                E.g., [CommonReportType.PURCHASE, CommonReportType.SALES].
        save_locally (bool): If True, saves the downloaded templates to disk.
        local_save_dir (Path | None): Directory to save the files.
                                          Defaults to './downloaded_files' if not provided
                                          and `save_locally` is True.

    Returns:
        dict[CommonReportType, BytesIO | None]: A dictionary where keys are template types
                                                  and values are BytesIO buffers of the
                                                  downloaded content, or None if download failed.

    """
    prepared_dir = _prepare_local_save_dir(
        save_locally=save_locally,
        local_save_dir=local_save_dir,
    )
    downloaded_buffers: dict[CommonReportType, BytesIO | None] = {}

    cbms_client = CBMSClient()
    taxpayer_client = TaxpayerClient()

    cbms_auth_needed = any(
        t in [CommonReportType.PURCHASE, CommonReportType.SALES] for t in template_types
    )
    if cbms_auth_needed:
        try:
            cbms_client.authenticate()
            logger.info("CBMS Client authenticated successfully for IRD templates.")
        except Exception:
            logger.exception(
                "Failed to authenticate CBMS Client. CBMS downloads may fail",
            )

    for template_type in template_types:
        buffer = None
        try:
            if template_type in [CommonReportType.PURCHASE, CommonReportType.SALES]:
                logger.info(
                    "Attempting to download CBMS template: %s",
                    template_type.name,
                )
                buffer = cbms_client.download_template(template_type)

            elif template_type == CommonReportType.LAKH_TRANSACTIONS:
                logger.info(
                    "Attempting to download Taxpayer template: %s",
                    template_type.name,
                )
                buffer = taxpayer_client.download_template(template_type)
            else:
                logger.warning(
                    "Unsupported IRD template type requested: '%s'. Skipping.",
                    template_type.name,
                )
                downloaded_buffers[template_type] = None
                continue

            downloaded_buffers[template_type] = buffer

            if buffer and save_locally and prepared_dir:
                file_path = (
                    prepared_dir
                    / f"{template_type.value}_template{template_type.file_extension}"
                )
                write_bytes_to_disk(buffer, file_path)
                logger.info("'%s' template saved to {file_path}", template_type.name)

        except Exception:
            logger.exception(
                "An unexpected error occurred processing '%s' template.",
                template_type.name,
            )
            downloaded_buffers[template_type] = None

    logger.info("IRD template download process completed.")
    return downloaded_buffers


def download_gdrive_file(
    file_pattern: str,
    *,
    page_size: int = settings.GOOGLE_DRIVE_PAGE_SIZE,  # Default to settings.GOOGLE_DRIVE_PAGE_SIZE, can be overridden
    save_locally: bool = True,
    local_save_dir: Path | None = None,
) -> Path | None:
    """
    Finds the latest Google Drive file matching a pattern and downloads it.

    Args:
        file_pattern (str): The regex pattern to match the file name.
        page_size (int): The number of files to retrieve from Drive to search through.
        save_locally (bool): If True, saves the downloaded file to disk. (Defaults to True).
        local_save_dir (Path | None): Directory to save the file.
                                          Defaults to `settings.default_download_path` if not provided.

    Returns:
        Path | None: The path to the downloaded file, or None if the download failed or file not found.

    """
    prepared_dir = _prepare_local_save_dir(
        save_locally=save_locally,
        local_save_dir=local_save_dir,
    )

    if not prepared_dir:
        logger.error(
            "Local save directory not prepared. Cannot download Google Drive file.",
        )
        return None

    try:
        # Safely resolve download account with fallback to None
        download_account = getattr(
            drive_settings, "DOWNLOAD_OAUTH_ACCOUNT", None
        ) or getattr(drive_settings, "DEFAULT_OAUTH_ACCOUNT", None)
        gdrive_service = get_oauth_drive_service(account=download_account)
        gdrive_client = GDriveClient(gdrive_service)

        latest_file_metadata = gdrive_client.find_latest_file(
            page_size=page_size,
            file_pattern=file_pattern,
        )

        if not latest_file_metadata:
            logger.warning(
                "No Google Drive file found matching pattern '%s'.",
                file_pattern,
            )
            return None

        expected_local_path = prepared_dir / latest_file_metadata.name

        if expected_local_path.is_file():
            logger.info(
                "Latest Google Drive file '%s' already exists locally at %s. Skipping download.",
                latest_file_metadata.name,
                expected_local_path.resolve(),
            )
            return expected_local_path

        logger.info(
            "Latest Google Drive file '%s' not found locally. Proceeding with download.",
            latest_file_metadata.name,
        )

        # Download the file using the GDriveClient's method
        downloaded_file_path = gdrive_client.download_file(
            file=latest_file_metadata,
            destination=prepared_dir,
        )
        logger.info(
            "Google Drive file '%s' downloaded successfully to %s",
            latest_file_metadata.name,
            downloaded_file_path.resolve(),
        )

    except ValueError:  # Catch invalid regex from gdrive_client
        logger.exception("Configuration error for Google Drive download")
        return None
    except Exception:
        logger.exception(
            "An unexpected error occurred during Google Drive file download",
        )
        return None

    else:
        return downloaded_file_path


def download_latest_mssql_backup(
    local_save_dir: Path | None = None,
    file_pattern: str | None = None,
) -> Path | None:
    """
    Downloads the latest MSSQL backup file from Google Drive.

    Args:
        local_save_dir: Directory to save the file.
        file_pattern: Override the default MSSQL backup file pattern from settings.

    Returns:
        The Path to the downloaded file if saved locally, None otherwise.

    """
    pattern = file_pattern if file_pattern else settings.MSSQL_BACKUP_FILE_PATTERN
    logger.info(
        "Attempting to download latest Google Drive file matching pattern '%s'...",
        pattern,
    )

    downloaded_path = download_gdrive_file(
        file_pattern=pattern,
        save_locally=True,
        local_save_dir=local_save_dir if local_save_dir else settings.BACKUP_DIR,
    )
    return downloaded_path
