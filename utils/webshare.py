import os
import logging

logger = logging.getLogger(__name__)


class Webshare:
    """Webshare rotating RESIDENTIAL proxy manager.

    Uses the Webshare rotating residential endpoint (p.webshare.io:80) which
    automatically assigns a different residential IP for each request.
    Datacenter IPs are blocked by Cloudflare on the Inovar portal, so we
    must use residential.
    """

    PROXY_HOST = "p.webshare.io"
    PROXY_PORT = "80"

    # Residential rotating credentials from the Webshare dashboard
    # (Proxy → Residential → Proxy Generator). Each TCP connection to
    # p.webshare.io:80 is assigned a different residential exit IP.
    PROXY_USER = "rmufozua"
    PROXY_PASS = "q82upl6ap5f81"

    def __init__(self):
        # Hardcoded to residential: datacenter IPs are blocked by Cloudflare on
        # the Inovar portal, so env-var overrides are intentionally ignored to
        # prevent an Azure app-setting from silently reverting to datacenter.
        self.proxy_user = self.PROXY_USER
        self.proxy_pass = self.PROXY_PASS

        legacy_user = os.getenv('WEBSHARE_PROXY_USER')
        if legacy_user and legacy_user != self.PROXY_USER:
            logger.warning(
                "Ignoring WEBSHARE_PROXY_USER=%r env var — forcing residential user %r.",
                legacy_user, self.PROXY_USER,
            )

        self.current_proxy = {
            'host': self.PROXY_HOST,
            'port': self.PROXY_PORT,
            'username': self.proxy_user,
            'password': self.proxy_pass,
        }

        logger.info(
            f"Webshare rotating residential proxy configured: "
            f"{self.PROXY_HOST}:{self.PROXY_PORT} (user={self.proxy_user})"
        )

    def get_proxy_dict(self):
        """Returns proxy configuration in requests format."""
        proxy_url = f"http://{self.proxy_user}:{self.proxy_pass}@{self.PROXY_HOST}:{self.PROXY_PORT}"
        return {
            'http': proxy_url,
            'https': proxy_url,
        }

    def switch_proxy(self):
        """Switch proxy - with rotating residential proxy, each request already gets a new IP."""
        logger.info("Rotating residential proxy: new IP will be assigned on next request")
        return self.get_proxy_dict()
