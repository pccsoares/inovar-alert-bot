import os
import logging

logger = logging.getLogger(__name__)


class Webshare:
    """Webshare rotating proxy manager.

    Uses the Webshare rotating proxy endpoint (p.webshare.io:80) which
    automatically assigns a different IP for each request.
    """

    PROXY_HOST = "p.webshare.io"
    PROXY_PORT = "80"

    def __init__(self):
        self.proxy_user = os.getenv('WEBSHARE_PROXY_USER')
        self.proxy_pass = os.getenv('WEBSHARE_PROXY_PASS')
        if not self.proxy_user or not self.proxy_pass:
            raise ValueError(
                "Webshare proxy credentials required. "
                "Set WEBSHARE_PROXY_USER and WEBSHARE_PROXY_PASS environment variables."
            )

        self.current_proxy = {
            'host': self.PROXY_HOST,
            'port': self.PROXY_PORT,
            'username': self.proxy_user,
            'password': self.proxy_pass
        }

        logger.info(f"Webshare rotating proxy configured: {self.PROXY_HOST}:{self.PROXY_PORT}")

    def get_proxy_dict(self):
        """Returns proxy configuration in requests format."""
        proxy_url = f"http://{self.proxy_user}:{self.proxy_pass}@{self.PROXY_HOST}:{self.PROXY_PORT}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def switch_proxy(self):
        """Switch proxy - with rotating proxy, each request already gets a new IP."""
        logger.info("Rotating proxy: new IP will be assigned on next request")
        return self.get_proxy_dict()
