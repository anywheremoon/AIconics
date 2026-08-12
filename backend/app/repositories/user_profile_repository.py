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


def update_event_count(db: Session, user_id: int, event_count: int) -> UserProfile | None:
    profile = find_by_user_id(db, user_id)
    if profile is None:
        return None
    profile.event_count = event_count
    db.flush()
    db.refresh(profile)
    return profile
