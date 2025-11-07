"""HTTP-triggered Azure Function for manual alert checks."""
import logging
import json
import azure.functions as func
from datetime import datetime

from services.alert_checker import AlertChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function for on-demand alert checking."""
    logger.info('HTTP trigger function received a request')

    try:
        # Run alert checker
        checker = AlertChecker()
        result = checker.check_alerts()

        # Prepare response
        response_data = {
            "status": "success" if result["success"] else "error",
            "timestamp": result["timestamp"],
            "new_absences": result["new_absences"],
            "new_behavior_alerts": result["new_behavior_alerts"],
            "email_sent": result["email_sent"],
            "error": result.get("error")
        }

        if result["success"]:
            logger.info(
                f"Alert check completed successfully. "
                f"New absences: {result['new_absences']}, "
                f"New behavior alerts: {result['new_behavior_alerts']}, "
                f"Email sent: {result['email_sent']}"
            )
            return func.HttpResponse(
                body=json.dumps(response_data, indent=2),
                mimetype="application/json",
                status_code=200
            )
        else:
            logger.error(f"Alert check failed: {result.get('error', 'Unknown error')}")
            return func.HttpResponse(
                body=json.dumps(response_data, indent=2),
                mimetype="application/json",
                status_code=500
            )

    except Exception as e:
        logger.error(f"Unhandled error in HTTP trigger: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }, indent=2),
            mimetype="application/json",
            status_code=500
        )
