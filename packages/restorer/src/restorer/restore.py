import logging
from pathlib import Path
from typing import TYPE_CHECKING

from dbkit.engine import get_engine
from dbkit.settings import MSSQLSettings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def restore_database(
    backup_path: Path | str,
    db_name: str,
    mssql_data_dir: Path | None = None,
) -> None:
    """
    Restore a SQL Server database from a .bak file.

    1. Connects to the 'master' database.
    2. Runs RESTORE FILELISTONLY to discover logical/physical names.
    3. Runs RESTORE DATABASE with MOVE ... TO ... and REPLACE, RECOVERY.
    """
    backup_path = Path(backup_path)
    db_settings = MSSQLSettings()

    mssql_data_dir = mssql_data_dir or db_settings.MSSQL_DATA_PATH

    try:
        engine: Engine = get_engine("master")  # Connect to master
        with engine.connect():
            logger.info(
                "Connected to 'master' on %s:%s",
                db_settings.DB_SERVER,
                db_settings.DB_PORT,
            )
    except SQLAlchemyError:
        logger.exception("Could not create engine for 'master'.")
        raise

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try:
            filelist_sql = text("RESTORE FILELISTONLY FROM DISK = :bak_path")
            logger.debug("Running FILELISTONLY for %s", backup_path)
            result = conn.execute(filelist_sql, {"bak_path": str(backup_path)})

            # Build a dict: Type → { logical_name, physical_name }
            files_info: dict[str, dict[str, str]] = {}
            for row in result:
                # row.Type is usually 'D' (data) or 'L' (log)
                files_info[row.Type] = {
                    "logical_name": row.LogicalName,
                    # Strip out any path and keep just the filename
                    "physical_name": Path(row.PhysicalName).name,
                }

            if "D" not in files_info or "L" not in files_info:
                msg = f"Could not find both data/log files in FILELISTONLY output: {files_info}"
                logger.error(msg)
                raise RuntimeError(msg)

            logger.info("FILELISTONLY retrieved: %s", files_info)

            data_target = mssql_data_dir / files_info["D"]["physical_name"]
            log_target = mssql_data_dir / files_info["L"]["physical_name"]

            logger.debug(
                "Target data file: %s, Target log file: %s",
                data_target,
                log_target,
            )

            raw_conn = conn.connection
            cursor = raw_conn.cursor()

            restore_sql_text = f"""
                RESTORE DATABASE [{db_name}]
                FROM DISK = ?
                WITH
                    MOVE ? TO ?,
                    MOVE ? TO ?,
                    REPLACE, RECOVERY;
            """
            restore_sql_params = (
                str(backup_path),
                files_info["D"]["logical_name"],
                str(data_target),
                files_info["L"]["logical_name"],
                str(log_target),
            )

            logger.info(
                "Restoring database '%s' from '%s'",
                db_name,
                backup_path.name,
            )

            cursor.execute(restore_sql_text, restore_sql_params)

            while cursor.nextset():
                logger.debug("Consumed additional result set during RESTORE.")

            cursor.close()

            logger.info(
                "Database '%s' successfully restored from %s",
                db_name,
                backup_path.name,
            )
        except SQLAlchemyError:
            logger.exception("Error during RESTORE commands.")
            raise

    #  Dispose the engine when done
    engine.dispose()
