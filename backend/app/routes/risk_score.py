from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event_model import Event
from app.schemas.risk_score_schema import (
    SuspiciousUserResponse,
    UserRiskScoreResponse,
)
from app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api",
    tags=["Risk Score"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/risk-score/{user_id}",
    response_model=UserRiskScoreResponse,
)
def get_user_risk_score(
    user_id: str,
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Risk score not found",
        )

    return UserRiskScoreResponse(
        user_id=event.user_id,
        risk_score=event.risk_score,
        risk_level=event.risk_level,
        is_anomaly=event.detect_anomaly,
        profile_deviation_score=event.profile_deviation_score,
        created_at=event.created_at,
    )


@router.get(
    "/risk-score/suspicious-users",
    response_model=list[SuspiciousUserResponse],
)
def get_suspicious_users(
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .filter(Event.risk_score >= 40)
        .order_by(Event.risk_score.desc(), Event.created_at.desc())
        .all()
    )

    return [
        SuspiciousUserResponse(
            user_id=event.user_id,
            risk_score=event.risk_score,
            risk_level=event.risk_level,
            is_anomaly=event.detect_anomaly,
            profile_deviation_score=event.profile_deviation_score,
            created_at=event.created_at,
        )
        for event in events
    ]