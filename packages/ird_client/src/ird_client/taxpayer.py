from io import BytesIO

import requests
from shared.constants import CommonReportType
from shared.exceptions import (
    FileValidationError,
    TemplateNotFoundError,
)
from shared.logger import LoggerFactory

from .session import CustomSession
from .settings import IrdClientSettings
from .utils import verify_hash

logger = LoggerFactory.get_logger(__name__)
settings = IrdClientSettings()


class TaxpayerClient(CustomSession):
    """Client for interacting with the Taxpayer Portal API to download templates."""

    def __init__(self, base_url: str = settings.TAXPAYER_BASE_URL):
        """Initializes the custom session optimized to connect to the TaxPayer portal."""
        super().__init__(base_url)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def download_template(self, report_type: CommonReportType) -> BytesIO | None:
        """
        Downloads a template file by name from the Taxpayer Portal and verifies its hash.

        Args:
            report_type (CommonReportType): The report type as an enum member (e.g., CommonReportType.LAKH_TRANSACTIONS)

        Returns:
            Optional[BytesIO]: A BytesIO object containing the file content if successful,
                               None otherwise.

        Raises:
            ValueError: If no endpoint is found for the template name in settings.
            requests.exceptions.RequestException: For network or HTTP errors during download.
            FileValidationError: If the downloaded file's hash does not match.
            TemplateNotFoundError: If the expected hash for the template is not found in settings.

        """
        try:
            endpoint = settings.taxpayer_template_endpoints.get(report_type)

            if not endpoint:
                msg = f"No endpoint found for template: {report_type.name} in TAXPAYER_TEMPLATE_ENDPOINTS."
                raise ValueError(msg)  # noqa: TRY301

            response = self.get(endpoint, timeout=60)
            response.raise_for_status()

            file_content = response.content
            verify_hash(file_content, report_type)

            return BytesIO(file_content)

        except (
            requests.exceptions.RequestException,
            FileValidationError,
            TemplateNotFoundError,
            ValueError,  # Include ValueError from endpoint check
        ):
            logger.exception("Template download failed for '%s'", report_type.name)
            return None
