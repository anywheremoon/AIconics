from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import user_session_repository
from app.services import device_trust_service, login_pattern_service


def create_login_session(
    db: Session,
    user_id: int,
    device_id: str,
    ip_address: str | None,
    location: str | None,
):
    trust_status = device_trust_service.assess_device(db, user_id, device_id)
    pattern = login_pattern_service.analyze_login_pattern(db, user_id, device_id)
    device_trust_service.record_device_use(db, user_id, device_id)

    user_session = user_session_repository.create_session(
        db,
        {
            "session_id": str(uuid4()),
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "location": location,
            "device_trust_status": trust_status.value,
            "repeated_login_detected": pattern["repeated_login_detected"],
            "account_switch_detected": pattern["account_switch_detected"],
            "recent_login_count": pattern["recent_login_count"],
            "recent_device_account_count": pattern[
                "recent_device_account_count"
            ],
        },
    )
    return user_session, trust_status, pattern


def validate_event_session(
    db: Session,
    session_id: str | None,
    user_id: int,
    device_id: str,
):
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The event is not linked to a login session",
        )

    user_session = user_session_repository.find_by_id(db, session_id)
    if user_session is None or user_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login session",
        )

    if user_session.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event device does not match the login session device",
        )
    return user_session
