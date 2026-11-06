"""Save hooks. Every flush in the process goes through these, whichever code made the change.

The order matters. Rules run first, because they create and change readings, and those
changes need an actor and an audit entry like any other.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.services import audit, readings


@event.listens_for(Session, "before_flush")
def _before_flush(session: Session, _context: object, _instances: object) -> None:
    readings.apply_rules_to_changed_releases(session)
    audit.stamp_actors(session)


@event.listens_for(Session, "after_flush")
def _after_flush(session: Session, _context: object) -> None:
    # After the flush, IDs and defaults exist while the change history is still there.
    audit.write_entries(session)
