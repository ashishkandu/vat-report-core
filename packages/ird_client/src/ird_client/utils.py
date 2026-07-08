import hashlib

from shared.constants import CommonReportType
from shared.exceptions import FileValidationError, TemplateNotFoundError
from shared.logger import LoggerFactory

from .settings import IrdClientSettings

logger = LoggerFactory.get_logger(__name__)
settings = IrdClientSettings()


def verify_hash(file_content: bytes, report_type: CommonReportType) -> None:
    """
    Verifies the hash of the file content against the expected hash.

    Args:
        file_content (bytes): The content of the file to verify.
        report_type (CommonReportType): The report type (enum member) to look up its expected hash.

    Raises:
        FileValidationError: If the downloaded hash does not match the expected hash.
        TemplateNotFoundError: If no expected hash is found for the template name.

    """
    downloaded_hash = hashlib.md5(file_content).hexdigest()
    expected_hash = get_expected_hash(report_type)

    if downloaded_hash != expected_hash:
        msg = f"Hash mismatch for {report_type.name}. Expected: {expected_hash}, Got: {downloaded_hash}"
        raise FileValidationError(msg)


def get_expected_hash(report_type: CommonReportType) -> str:
    """
    Retrieves the expected hash value for a template.

    Args:
        report_type (CommonReportType): The enum value representing the template type.

    Returns:
        str: The expected MD5 hash string.

    Raises:
        TemplateNotFoundError: If no hash value is found for the given template name in settings.

    """
    try:
        return settings.hash_value[report_type]
    except KeyError as err:
        msg = f"No hash value found for {report_type.name} in settings."
        raise TemplateNotFoundError(msg) from err
