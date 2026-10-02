from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_model import Event


def get_latest_behavior_identity(
    db: Session,
    *,
    user_id: int,
    session_id: str,
) -> dict:
    """Return the user's globally latest event for the requested session.

    A historical session cannot be selected to reuse an older, safer behavior
    score. The caller must submit a fresh behavior event for its session first.
    """
    if not session_id:
        raise ValueError("An active session ID is required")

    event = (
        db.query(Event)
        .filter(Event.user_id == str(user_id))
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No behavior event is available for transaction risk assessment",
        )

    if event.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The latest behavior event does not belong to the requested "
                "session; submit a fresh event before transferring"
            ),
        )

    reasons = event.reasons or []
    if not isinstance(reasons, list):
        raise ValueError("Stored behavior risk reasons must be a list")

    return {
        "behavior_score": event.behavior_score,
        "identity_score": event.identity_score,
        "behavior_reasons": [
            reason
            for reason in reasons
            if isinstance(reason, dict)
            and reason.get("score_type") == "BEHAVIOR"
        ],
        "identity_reasons": [
            reason
            for reason in reasons
            if isinstance(reason, dict)
            and reason.get("score_type") == "IDENTITY"
        ],
        "event_id": event.id,
    }
