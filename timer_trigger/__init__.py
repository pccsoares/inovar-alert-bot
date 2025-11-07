"""Timer-triggered Azure Function to check for alerts daily at 14:00."""
import logging
import azure.functions as func
from datetime import datetime

from services.alert_checker import AlertChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(mytimer: func.TimerRequest) -> None:
    """Timer trigger function that runs daily at 14:00 UTC."""
    utc_timestamp = datetime.utcnow().replace(tzinfo=None).isoformat()

    if mytimer.past_due:
        logger.warning('The timer is past due!')

    logger.info(f'Timer trigger function started at {utc_timestamp}')

    try:
        # Run alert checker
        checker = AlertChecker()
        result = checker.check_alerts()

        # Log results
        if result["success"]:
            logger.info(
                f"Alert check completed successfully. "
                f"New absences: {result['new_absences']}, "
                f"New behavior alerts: {result['new_behavior_alerts']}, "
                f"Email sent: {result['email_sent']}"
            )
        else:
            logger.error(f"Alert check failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Unhandled error in timer trigger: {e}", exc_info=True)

    logger.info(f'Timer trigger function completed at {datetime.utcnow().isoformat()}')
