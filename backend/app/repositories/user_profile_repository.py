from sqlalchemy.orm import Session

from app.models.user_profile_model import UserProfile


def create_profile(db: Session, profile_data: dict) -> UserProfile:
    profile = UserProfile(**profile_data)
    db.add(profile)
    db.flush()
    db.refresh(profile)
    return profile


def find_by_user_id(db: Session, user_id: int) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def update_behavior_profile(
    db: Session,
    user_id: int,
    *,
    avg_typing_speed: float,
    avg_hold_time: float,
    avg_flight_time: float,
    avg_mouse_move_count: float,
    avg_click_count: float,
) -> UserProfile | None:
    profile = find_by_user_id(db, user_id)
    if profile is None:
        return None

    profile.avg_typing_speed = avg_typing_speed
    profile.avg_hold_time = avg_hold_time
    profile.avg_flight_time = avg_flight_time
    profile.avg_mouse_move_count = avg_mouse_move_count
    profile.avg_click_count = avg_click_count
    db.flush()
    return profile


def increment_event_count(db: Session, user_id: int) -> UserProfile | None:
    profile = find_by_user_id(db, user_id)
    if profile is None:
        return None
    profile.event_count += 1
    db.flush()
    db.refresh(profile)
    return profile


def update_event_count(db: Session, user_id: int, event_count: int) -> UserProfile | None:
    """Set an explicit count (kept for compatibility with existing callers)."""
    profile = find_by_user_id(db, user_id)
    if profile is None:
        return None
    profile.event_count = event_count
    db.flush()
    db.refresh(profile)
    return profile
