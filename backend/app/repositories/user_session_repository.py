from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user_session_model import UserSession


def create_session(db: Session, session_data: dict) -> UserSession:
    user_session = UserSession(**session_data)
    db.add(user_session)
    db.flush()
    db.refresh(user_session)
    return user_session


def find_by_id(db: Session, session_id: str) -> UserSession | None:
    return (
        db.query(UserSession)
        .filter(UserSession.session_id == session_id)
        .first()
    )


def find_recent_by_user(
    db: Session, user_id: int, since: datetime
) -> list[UserSession]:
    return (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.login_at >= since)
        .order_by(UserSession.login_at.desc())
        .all()
    )


def find_recent_by_device(
    db: Session, device_id: str, since: datetime
) -> list[UserSession]:
    return (
        db.query(UserSession)
        .filter(UserSession.device_id == device_id, UserSession.login_at >= since)
        .order_by(UserSession.login_at.desc())
        .all()
    )
