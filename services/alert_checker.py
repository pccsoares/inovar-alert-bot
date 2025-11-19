"""Alert checker service - orchestrates scraping, database, and notifications."""
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from models.database import AlertEvent, init_db, is_new_event, save_event, mark_event_notified
from services.scraper_lightweight import InovarScraperLightweight
from services.email_notifier import EmailNotifier
from utils.config import get_config

logger = logging.getLogger(__name__)


class AlertChecker:
    """Main alert checking orchestrator."""

    def __init__(self):
        self.config = get_config()
        self.new_absences: List[Dict[str, Any]] = []
        self.new_behavior_alerts: List[Dict[str, Any]] = []

    def check_alerts(self) -> Dict[str, Any]:
        """Main method to check for alerts."""
        result = {
            "success": False,
            "new_absences": 0,
            "new_behavior_alerts": 0,
            "email_sent": False,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Initialize database
            logger.info("Initializing database...")
            init_db(self.config.database_path)

            # Scrape portal
            logger.info("Starting scraping process...")
            scrape_results = self._scrape_portal()

            if not scrape_results["success"]:
                error_msg = scrape_results.get("error", "Scraping failed")
                result["error"] = error_msg
                logger.error(f"Scraping failed: {result['error']}")

                # Send failure notification
                self._send_failure_notification(
                    error_message=f"Falha ao obter dados do portal Inovar: {error_msg}",
                    error_details="O bot não conseguiu aceder ao portal ou fazer login. Verifique as credenciais e o estado do proxy."
                )

                return result

            # Process absences
            all_absences = scrape_results.get("absences", [])
            logger.info(f"Processing {len(all_absences)} absences...")
            self.new_absences = self._filter_new_events(all_absences, "absence")

            # Process behavior alerts
            all_alerts = scrape_results.get("behavior_alerts", [])
            logger.info(f"Processing {len(all_alerts)} behavior alerts...")
            self.new_behavior_alerts = self._filter_new_events(all_alerts, "behavior_alert")

            # Update result counts
            result["new_absences"] = len(self.new_absences)
            result["new_behavior_alerts"] = len(self.new_behavior_alerts)

            logger.info(
                f"Found {result['new_absences']} new absences and "
                f"{result['new_behavior_alerts']} new behavior alerts"
            )

            # Send email if there are new events
            if self.new_absences or self.new_behavior_alerts:
                logger.info("New events detected, sending email...")
                email_sent = self._send_notification()
                result["email_sent"] = email_sent

                if email_sent:
                    # Mark events as notified
                    self._mark_events_notified()
            else:
                logger.info("No new events detected, skipping email")

            result["success"] = True

        except Exception as e:
            logger.error(f"Error in check_alerts: {e}", exc_info=True)
            result["error"] = str(e)

            # Send failure notification for unexpected errors
            import traceback
            self._send_failure_notification(
                error_message=f"Erro inesperado no bot: {str(e)}",
                error_details=traceback.format_exc()
            )

        return result

    def _scrape_portal(self) -> Dict[str, Any]:
        """Scrape the Inovar portal using lightweight API-based approach."""
        try:
            # Force proxy usage (auto-detection wasn't working reliably in Azure)
            import os
            is_azure = os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('WEBSITE_INSTANCE_ID')
            logger.info(f"Environment check: is_azure={bool(is_azure)}")

            with InovarScraperLightweight(
                username=self.config.inovar_username,
                password=self.config.inovar_password,
                login_url=self.config.inovar_login_url,
                home_url=self.config.inovar_home_url,
                use_proxy=True  # Always use proxy in Azure to bypass Cloudflare
            ) as scraper:
                return scraper.scrape_all()

        except Exception as e:
            logger.error(f"Error scraping portal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "absences": [],
                "behavior_alerts": []
            }

    def _filter_new_events(
        self,
        events: List[Dict[str, Any]],
        event_type: str
    ) -> List[Dict[str, Any]]:
        """Filter events to only include new ones not in database."""
        new_events = []

        for event in events:
            # Generate unique event ID
            event_id = self._generate_event_id(event, event_type)

            # Check if event is new
            if is_new_event(event_id, self.config.database_path):
                # Save to database
                alert_event = AlertEvent(
                    event_id=event_id,
                    event_type=event_type,
                    date=event.get("date", datetime.now().strftime("%Y-%m-%d")),
                    description=event.get("description", ""),
                    raw_data=json.dumps(event),
                    notified=False
                )

                if save_event(alert_event, self.config.database_path):
                    new_events.append(event)
                    logger.info(f"New event detected: {event_id}")
                else:
                    logger.warning(f"Failed to save event: {event_id}")
            else:
                logger.debug(f"Event already exists: {event_id}")

        return new_events

    def _generate_event_id(self, event: Dict[str, Any], event_type: str) -> str:
        """Generate unique event ID."""
        # Create ID based on event type, date, and description
        date = event.get("date", "unknown")
        description = event.get("description", "")
        subject = event.get("subject", "")

        # Create a unique identifier
        id_parts = [event_type, date, description[:50], subject]
        event_id = "_".join([str(p).replace(" ", "_") for p in id_parts if p])

        return event_id

    def _send_notification(self) -> bool:
        """Send email notification."""
        try:
            recipients = self.config.get_email_recipients()

            if not recipients:
                logger.error("No email recipients configured")
                return False

            notifier = EmailNotifier(
                smtp_host=self.config.smtp_host,
                smtp_port=self.config.smtp_port,
                smtp_user=self.config.smtp_user,
                smtp_pass=self.config.smtp_pass,
                smtp_from=self.config.smtp_from
            )

            return notifier.send_alert_email(
                recipients=recipients,
                absences=self.new_absences,
                behavior_alerts=self.new_behavior_alerts
            )

        except Exception as e:
            logger.error(f"Error sending notification: {e}", exc_info=True)
            return False

    def _mark_events_notified(self):
        """Mark all new events as notified in database."""
        try:
            for event in self.new_absences + self.new_behavior_alerts:
                event_id = self._generate_event_id(
                    event,
                    "absence" if event in self.new_absences else "behavior_alert"
                )
                mark_event_notified(event_id, self.config.database_path)
        except Exception as e:
            logger.error(f"Error marking events as notified: {e}")

    def _send_failure_notification(self, error_message: str, error_details: str = None) -> bool:
        """Send email notification when the bot fails."""
        try:
            recipients = self.config.get_email_recipients()

            if not recipients:
                logger.error("No email recipients configured for failure notification")
                return False

            notifier = EmailNotifier(
                smtp_host=self.config.smtp_host,
                smtp_port=self.config.smtp_port,
                smtp_user=self.config.smtp_user,
                smtp_pass=self.config.smtp_pass,
                smtp_from=self.config.smtp_from
            )

            return notifier.send_failure_email(
                recipients=recipients,
                error_message=error_message,
                error_details=error_details
            )

        except Exception as e:
            logger.error(f"Error sending failure notification: {e}", exc_info=True)
            # Don't raise - we don't want a failure notification error to break everything
            return False
