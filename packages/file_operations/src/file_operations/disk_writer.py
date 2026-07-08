from io import BytesIO
from pathlib import Path

from shared.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


def write_bytes_to_disk(buffer: BytesIO, filepath: Path) -> Path:
    """
    Write bytes-formatted data to the provided filepath.

    Args:
        buffer (BytesIO): The bytes-formatted data to be written.
        filepath (Path): The file path to write the data to.

    Returns:
        Path: The path to the written file.

    Raises:
        FileNotFoundError: If the parent directories cannot be created.
        PermissionError: If there is an error writing to the file.
        OSError: For other unexpected OS errors.

    """
    # Log the action
    logger.debug("Saving contents to %s", filepath.name)

    # Write the data to the file
    parent_path = filepath.parent
    if not parent_path.exists():
        try:
            parent_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.exception("Error creating parent directories for %s", filepath)
            msg = f"Failed to create parent directories for {filepath}"
            raise FileNotFoundError(msg) from e

    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    try:
        with tmp_path.open("wb") as file:
            file.write(buffer.getvalue())
        tmp_path.rename(filepath)
    except PermissionError:
        logger.exception("Error writing to file '%s'", filepath)
        raise
    except OSError:
        logger.exception("An unexpected OS error occurred writing to '%s'", filepath)
        raise

    # Log the completion
    logger.info("File '%s' write completed!", filepath.name)

    return filepath
