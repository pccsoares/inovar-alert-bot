"""Configuration management for the application."""
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""

    def __init__(self):
        # Inovar portal credentials
        self.inovar_username = os.getenv("INOVAR_USERNAME", "")
        self.inovar_password = os.getenv("INOVAR_PASSWORD", "")
        self.inovar_login_url = os.getenv(
            "INOVAR_LOGIN_URL",
            "https://aevf.inovarmais.com/consulta/app/index.html#/login"
        )
        self.inovar_home_url = os.getenv(
            "INOVAR_HOME_URL",
            "https://aevf.inovarmais.com/consulta/app/index.html#/home"
        )

        # SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.smtp_from = os.getenv("SMTP_FROM", "")

        # Email recipients
        self.alert_email_to = os.getenv("ALERT_EMAIL_TO", "")
        self.alert_email_to_fallback = os.getenv("ALERT_EMAIL_TO_FALLBACK", "")

        # Database
        # Use persistent storage in Azure Functions (/home is backed by Azure Files)
        # Local development uses current directory
        is_azure = os.getenv('WEBSITE_INSTANCE_ID') is not None
        default_db_path = "/home/data/alerts.db" if is_azure else "alerts.db"
        self.database_path = os.getenv("DATABASE_PATH", default_db_path)

        logger.info(f"Database path configured: {self.database_path}")

        # Timezone
        self.timezone = os.getenv("TIMEZONE", "Europe/Lisbon")

        # Validate required config
        self._validate()

    def _validate(self):
        """Validate required configuration."""
        missing = []

        if not self.inovar_username:
            missing.append("INOVAR_USERNAME")
        if not self.inovar_password:
            missing.append("INOVAR_PASSWORD")
        if not self.smtp_host:
            missing.append("SMTP_HOST")
        if not self.smtp_user:
            missing.append("SMTP_USER")
        if not self.smtp_pass:
            missing.append("SMTP_PASS")
        if not self.smtp_from:
            missing.append("SMTP_FROM")

        if missing:
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not self.alert_email_to and not self.alert_email_to_fallback:
            logger.warning(
                "No email recipient configured! Set ALERT_EMAIL_TO or ALERT_EMAIL_TO_FALLBACK"
            )

    def get_email_recipients(self) -> list[str]:
        """Get list of email recipients (primary + fallback)."""
        recipients = []
        if self.alert_email_to:
            recipients.append(self.alert_email_to)
        if self.alert_email_to_fallback:
            recipients.append(self.alert_email_to_fallback)
        return recipients


# Global config instance
_config = None


def get_config() -> Config:
    """Get application configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
        logger.info("Configuration loaded")
    return _config
