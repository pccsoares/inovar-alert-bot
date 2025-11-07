"""Database models for storing alert events."""
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session, select

logger = logging.getLogger(__name__)


class AlertEvent(SQLModel, table=True):
    """Model for tracking alert events (absences and behavior alerts)."""

    __tablename__ = "alert_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(unique=True, index=True)  # Unique identifier from API/scraping
    event_type: str = Field(index=True)  # "absence" or "behavior_alert"
    date: str  # Event date (YYYY-MM-DD format)
    description: str  # Event description/details
    raw_data: Optional[str] = None  # JSON string of raw event data
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    notified: bool = Field(default=False)  # Whether email was sent for this event


# Global engine instance
_engine = None


def get_engine(database_path: str = "alerts.db"):
    """Get or create database engine."""
    global _engine
    if _engine is None:
        database_url = f"sqlite:///{database_path}"
        _engine = create_engine(database_url, echo=False)
        logger.info(f"Database engine created: {database_url}")
    return _engine


def init_db(database_path: str = "alerts.db"):
    """Initialize database and create tables."""
    engine = get_engine(database_path)
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized successfully")


def is_new_event(event_id: str, database_path: str = "alerts.db") -> bool:
    """Check if an event is new (not in database)."""
    engine = get_engine(database_path)
    with Session(engine) as session:
        statement = select(AlertEvent).where(AlertEvent.event_id == event_id)
        existing = session.exec(statement).first()
        return existing is None


def save_event(event: AlertEvent, database_path: str = "alerts.db") -> bool:
    """Save a new event to database. Returns True if saved, False if duplicate."""
    engine = get_engine(database_path)
    try:
        with Session(engine) as session:
            # Check if already exists
            if not is_new_event(event.event_id, database_path):
                logger.info(f"Event {event.event_id} already exists, skipping")
                return False

            session.add(event)
            session.commit()
            logger.info(f"Event {event.event_id} saved successfully")
            return True
    except Exception as e:
        logger.error(f"Error saving event {event.event_id}: {e}")
        return False


def mark_event_notified(event_id: str, database_path: str = "alerts.db"):
    """Mark an event as notified."""
    engine = get_engine(database_path)
    with Session(engine) as session:
        statement = select(AlertEvent).where(AlertEvent.event_id == event_id)
        event = session.exec(statement).first()
        if event:
            event.notified = True
            session.add(event)
            session.commit()
            logger.info(f"Event {event_id} marked as notified")
