from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories import user_session_repository


LOGIN_PATTERN_WINDOW_MINUTES = 10


def analyze_login_pattern(
    db: Session,
    user_id: int,
    device_id: str,
    *,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(minutes=LOGIN_PATTERN_WINDOW_MINUTES)
    recent_user_sessions = user_session_repository.find_recent_by_user(
        db, user_id, since
    )
    recent_device_sessions = user_session_repository.find_recent_by_device(
        db, device_id, since
    )

    device_user_ids = {session.user_id for session in recent_device_sessions}
    device_user_ids.add(user_id)

    return {
        "window_minutes": LOGIN_PATTERN_WINDOW_MINUTES,
        "repeated_login_detected": len(recent_user_sessions) >= 1,
        "account_switch_detected": len(device_user_ids) >= 2,
        "recent_login_count": len(recent_user_sessions) + 1,
        "recent_device_account_count": len(device_user_ids),
    }