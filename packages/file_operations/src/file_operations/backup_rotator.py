import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path

from shared.logger import LoggerFactory

from .settings import FileOperationsSettings

logger = LoggerFactory.get_logger(__name__)
settings = FileOperationsSettings()


def rotate_backups(
    backup_dir: Path,
    max_age_days: int = settings.max_backup_age_days,
) -> tuple[int, int]:
    """Deletes backup files older than max_age_days."""
    if not backup_dir.is_dir():
        logger.warning(
            "Backup directory '%s' does not exist or is not a directory. Skipping backup rotation.",
            backup_dir,
        )
        return 0, 0

    logger.info(
        "Rotating backups in '%s' (max age: %s days)...",
        backup_dir,
        max_age_days,
    )
    # settings.local_time_zone is a string; convert it to a tzinfo object
    now = datetime.now(tz=zoneinfo.ZoneInfo(settings.local_time_zone))
    deleted_count = 0
    errors_count = 0
    scanned_count = 0

    for file in backup_dir.glob("*.bak"):
        if file.is_file():
            scanned_count += 1
            try:
                # Use file.stat().st_mtime for modification time
                file_age = now - datetime.fromtimestamp(
                    file.stat().st_mtime,
                    tz=zoneinfo.ZoneInfo(settings.local_time_zone),
                )
                if file_age > timedelta(days=max_age_days):
                    file.unlink()  # Deletes the file
                    logger.info("Deleted old backup: '%s'", file.name)
                    deleted_count += 1
            except FileNotFoundError:
                logger.warning(
                    "File '%s' disappeared during rotation. Skipping.",
                    file.name,
                )
            except OSError:
                logger.exception("Error deleting backup '%s'", file.name)
                errors_count += 1
            except Exception:
                logger.exception(
                    "An unexpected error occurred processing '%s'",
                    file.name,
                )
                errors_count += 1

    logger.info("Scanned %d .bak files.", scanned_count)

    if deleted_count > 0:
        logger.info("Backup rotation completed. %s old backups deleted.", deleted_count)
    elif errors_count > 0:
        logger.warning("Backup rotation completed with %s errors.", errors_count)
    else:
        logger.info("No old backups found to delete.")

    return deleted_count, errors_count
