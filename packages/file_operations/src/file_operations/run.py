from shared import SharedSettings

from .backup_rotator import rotate_backups

settings = SharedSettings()


def run() -> None:
    rotate_backups(settings.BACKUP_DIR)
