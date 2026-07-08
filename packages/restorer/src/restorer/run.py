from shared.config.base import SharedSettings

from . import restore_database

settings = SharedSettings()

database_name = "VatBillingSoftware"
backup_path = settings.MSSQL_BACKUP_MOUNT / "VatBillingSoftware_20820216_213139.bak"


def run() -> None:
    restore_database(backup_path, database_name)
