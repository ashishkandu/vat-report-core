from urllib.parse import urljoin

from requests import Session
from requests.adapters import HTTPAdapter, Retry

retry_strategy = Retry(
    total=4,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)

adapter = HTTPAdapter(max_retries=retry_strategy)


class CustomSession(Session):
    """A custom requests.Session class with retry logic and a base URL."""

    def __init__(self, base_url: str):
        super().__init__()
        self.mount("http://", adapter)
        self.mount("https://", adapter)
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        """
        Constructs and sends a Request, joining the URL with the base_url.

        :param method: HTTP method for the new Request object.
        :param url: URL for the new Request object (can be relative).
        :param args: Positional arguments for requests.Session.request.
        :param kwargs: Keyword arguments for requests.Session.request.
        """
        url = urljoin(self.base_url, url)
        return super().request(method, url, *args, **kwargs)
