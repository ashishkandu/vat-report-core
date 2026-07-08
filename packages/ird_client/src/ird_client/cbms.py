from io import BytesIO

import requests
from shared.constants import CommonReportType
from shared.exceptions import (
    FileValidationError,
    TemplateNotFoundError,
)
from shared.logger import LoggerFactory

from .auth import CBMSAuth
from .session import CustomSession
from .settings import IrdClientSettings
from .utils import verify_hash

logger = LoggerFactory.get_logger(__name__)
settings = IrdClientSettings()


class CBMSClient(CustomSession):
    """Client for interacting with the CBMS API to download templates."""

    def __init__(self, base_url: str = settings.CBMS_BASE_URL):
        super().__init__(base_url)
        self.auth: CBMSAuth | None = None

    def authenticate(self):
        """Authenticates the client using CBMSAuth and sets the session's authentication."""
        self.auth = CBMSAuth().fetch_token(
            self,
        )  # Pass self (the CustomSession instance)
        return self  # Return self for method chaining

    def download_template(self, report_type: CommonReportType) -> BytesIO | None:
        """
        Downloads a template file by name from CBMS and verifies its hash.

        Args:
            report_type (CommonReportType): The report type as an enum value.

        Returns:
            Optional[BytesIO]: A BytesIO object containing the file content if successful,
                               None otherwise.

        Raises:
            ValueError: If no endpoint is found for the template name in settings.
            requests.exceptions.RequestException: For network or HTTP errors during download.
            FileValidationError: If the downloaded file's hash does not match.
            TemplateNotFoundError: If the expected hash for the template is not found in settings.

        """
        if not self.auth:
            logger.warning(
                "Attempting to download template without authentication. Call .authenticate() first.",
            )
            # Depending on API, you might want to raise an error here.
            # For now, it will likely fail with a 401 Unauthorized if auth is truly needed.

        try:
            endpoint = settings.cbms_template_endpoints.get(report_type)

            if not endpoint:
                msg = f"No endpoint found for template: {report_type} in CBMS_TEMPLATE_ENDPOINTS."
                raise ValueError(msg)  # noqa: TRY301

            response = self.get(endpoint, auth=self.auth, timeout=60)
            response.raise_for_status()

            file_content = response.content
            verify_hash(file_content, report_type)

            return BytesIO(file_content)

        except requests.exceptions.RequestException:
            # Catch RequestException broadly for network errors, timeouts, HTTP errors
            logger.exception(
                "Network or HTTP error during template download for '%s'",
                report_type,
            )
            return None
        except (FileValidationError, TemplateNotFoundError):
            # Catch specific application-level validation/lookup errors
            logger.exception(
                "Template validation/lookup failed for '%s'",
                report_type,
            )
            return None
        except Exception:
            # Catch any other unexpected errors and log with traceback
            logger.exception(
                "An unexpected error occurred during template download for '%s'",
                report_type,
            )
            return None
