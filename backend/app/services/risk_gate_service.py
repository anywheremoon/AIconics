from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_model import Event
from app.models.user_model import User


BLOCKED_RISK_LEVELS = frozenset({"MEDIUM", "HIGH", "CRITICAL"})


def lock_user_for_risk_transition(db: Session, user_id: int) -> User:
    """Serialize risk-event writes and money-moving decisions for one user."""
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
        )
    return user


def ensure_transaction_allowed(db: Session, user_id: int) -> Event | None:
    """Lock the user and reject transactions from a blocked latest state."""
    lock_user_for_risk_transition(db, user_id)

    latest_event = (
        db.query(Event)
        .filter(Event.user_id == str(user_id))
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )

    # Users without behavior events retain the existing transaction policy.
    if latest_event is None:
        return None

    if latest_event.risk_level in BLOCKED_RISK_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transactions are blocked because the latest risk level is elevated",
        )

    return latest_event
