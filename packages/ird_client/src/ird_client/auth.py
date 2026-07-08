import requests
from requests.auth import AuthBase
from shared.logger import LoggerFactory

from .session import CustomSession
from .settings import IrdClientSettings

logger = LoggerFactory.get_logger(__name__)
settings = IrdClientSettings()


class CBMSAuth(AuthBase):
    """Attaches a Bearer token to the Authorization header and handles token fetching."""

    def __init__(self, token: str | None = None):
        self.token = token

    def __call__(self, r):
        """Method called by requests to apply authentication."""
        if self.token:
            r.headers["Authorization"] = f"Bearer {self.token}"
        return r

    def fetch_token(self, cbms_client: CustomSession):
        """
        Fetches and sets the authentication token.

        Args:
            cbms_client (CustomSession): An initialized CustomSession instance
                                         to make the login request.

        Returns:
            CBMSAuth: Returns self for method chaining.

        Raises:
            requests.exceptions.RequestException: For network or HTTP errors during login.
            requests.exceptions.HTTPError: If login fails based on API response.

        """
        pan = settings.TAXPAYER_ID
        login_id = settings.CBMS_USERNAME
        password = settings.CBMS_PASSWORD

        if not all([pan, login_id, password]):
            logger.error(
                "Missing PAN, LoginId, or password environment variables for CBMS login.",
            )
            msg = "Authentication credentials (PAN, LoginId, password) are not set in environment variables."
            raise ValueError(msg)

        json_data = {
            "PAN": pan,
            "LoginId": login_id,
            "password": password,
            "isSuperAdmin": False,
        }
        try:
            # Use the provided cbms_client instance
            response = cbms_client.post(
                settings.CBMS_LOGIN_ENDPOINT,
                json=json_data,
                timeout=30,
            )
            log_msg = f"{response.request.method} {response.url} [status:{response.status_code} request:{response.elapsed.total_seconds():.3f}s]"
            logger.info(log_msg)
            response.raise_for_status()  # Raise for 4xx/5xx status codes

            response_data = response.json()

            if not response_data.get("isSucess"):
                message = response_data.get("message", "Unknown login error")
                msg = f"Login failed: {message}"
                raise requests.exceptions.HTTPError(
                    msg,
                    response=response,
                )

            self.token = response_data["token"]
            user_name = response_data.get("responseData", {}).get(
                "userName",
                "Unknown User",
            )
            logger.info("Successfully logged in as %s", user_name)

        except requests.exceptions.RequestException:
            logger.exception("Login failed")
            raise

        else:
            return self
