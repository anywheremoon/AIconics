from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user_session_model import UserSession
from app.repositories import user_session_repository
from app.services import device_trust_service, login_pattern_service
from app.services.risk_gate_service import lock_user_for_risk_transition


def create_login_session(
    db: Session,
    user_id: int,
    device_id: str,
    ip_address: str | None,
    location: str | None,
):
    trust_status = device_trust_service.assess_device(
        db, user_id, device_id
    )

    pattern = login_pattern_service.analyze_login_pattern(
        db, user_id, device_id
    )

    device_trust_service.record_device_use(
        db, user_id, device_id
    )

    user_session = user_session_repository.create_session(
        db,
        {
            "session_id": str(uuid4()),
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "location": location,
            "device_trust_status": trust_status.value,
            "repeated_login_detected": (
                pattern["repeated_login_detected"]
            ),
            "account_switch_detected": (
                pattern["account_switch_detected"]
            ),
            "recent_login_count": pattern["recent_login_count"],
            "recent_device_account_count": (
                pattern["recent_device_account_count"]
            ),
        },
    )

    return user_session, trust_status, pattern


def _find_owned_session(
    db: Session,
    *,
    session_id: str | None,
    user_id: int,
):
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A login session is required",
        )

    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == str(session_id),
            UserSession.user_id == user_id,
        )
        .populate_existing()
        .first()
    )

    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login session",
        )

    return user_session


def validate_active_session(
    db: Session,
    *,
    session_id: str | None,
    user_id: int,
):
    lock_user_for_risk_transition(db, user_id)

    user_session = _find_owned_session(
        db,
        session_id=session_id,
        user_id=user_id,
    )

    if not user_session.is_active or user_session.logout_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The login session has ended",
        )

    return user_session


def end_login_session(
    db: Session,
    *,
    session_id: str,
    user_id: int,
):
    """
    해당 사용자의 세션 하나를 종료한다.
    commit과 rollback은 호출자가 수행한다.
    """
    lock_user_for_risk_transition(db, user_id)

    user_session = _find_owned_session(
        db,
        session_id=session_id,
        user_id=user_id,
    )

    # 이미 종료된 세션의 로그아웃 요청도 성공으로 처리한다.
    user_session.is_active = False

    if user_session.logout_at is None:
        user_session.logout_at = datetime.now(timezone.utc)

    db.flush()
    return user_session


def validate_event_session(
    db: Session,
    session_id: str | None,
    user_id: int,
    device_id: str,
):
    user_session = validate_active_session(
        db,
        session_id=session_id,
        user_id=user_id,
    )

    if user_session.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event device does not match the login session device",
        )

    return user_session