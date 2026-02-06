"""Database using Azure Table Storage for tracking alert events."""
import json
import logging
import os
from datetime import datetime

from azure.data.tables import TableServiceClient, TableClient

logger = logging.getLogger(__name__)

TABLE_NAME = "alertevents"

_table_client: TableClient = None


def _get_table_client() -> TableClient:
    """Get or create the Azure Table Storage client."""
    global _table_client
    if _table_client is None:
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            raise ValueError("AzureWebJobsStorage connection string not set")

        service = TableServiceClient.from_connection_string(conn_str)
        service.create_table_if_not_exists(TABLE_NAME)
        _table_client = service.get_table_client(TABLE_NAME)
        logger.info(f"Azure Table Storage client initialized: {TABLE_NAME}")
    return _table_client


def init_db(database_path: str = None):
    """Initialize the table (create if not exists). database_path is ignored (kept for compatibility)."""
    client = _get_table_client()

    # Log existing event count for diagnostics
    count = 0
    for _ in client.query_entities("PartitionKey eq 'event'", select=["RowKey"], results_per_page=1000):
        count += 1
    logger.info(f"Database initialized (Azure Table Storage). Existing events: {count}")


def is_new_event(event_id: str, database_path: str = None) -> bool:
    """Check if an event is new (not in table)."""
    client = _get_table_client()
    try:
        client.get_entity(partition_key="event", row_key=event_id)
        return False
    except Exception:
        return True


def save_event_record(
    event_id: str,
    event_type: str,
    date: str,
    description: str,
    raw_data: str = None,
    database_path: str = None
) -> bool:
    """Save a new event to Azure Table Storage. Returns True if saved, False if duplicate."""
    client = _get_table_client()
    try:
        # Check if already exists
        if not is_new_event(event_id):
            logger.info(f"Event {event_id} already exists, skipping")
            return False

        entity = {
            "PartitionKey": "event",
            "RowKey": event_id,
            "event_type": event_type,
            "date": date,
            "description": description,
            "raw_data": raw_data or "",
            "first_seen": datetime.utcnow().isoformat(),
            "notified": False
        }
        client.create_entity(entity)

        # Verify write
        try:
            client.get_entity(partition_key="event", row_key=event_id)
            logger.info(f"Event {event_id} saved and verified")
            return True
        except Exception:
            logger.error(f"Event {event_id} save NOT verified!")
            return False

    except Exception as e:
        # ResourceExistsError means duplicate - that's fine
        if "EntityAlreadyExists" in str(e) or "conflict" in str(e).lower():
            logger.info(f"Event {event_id} already exists (conflict), skipping")
            return False
        logger.error(f"Error saving event {event_id}: {e}")
        return False


def mark_event_notified(event_id: str, database_path: str = None):
    """Mark an event as notified."""
    client = _get_table_client()
    try:
        entity = client.get_entity(partition_key="event", row_key=event_id)
        entity["notified"] = True
        client.update_entity(entity)
        logger.info(f"Event {event_id} marked as notified")
    except Exception as e:
        logger.error(f"Error marking event {event_id} as notified: {e}")
