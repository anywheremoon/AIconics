from sqlalchemy.orm import Session

from app.models.user_model import User


def find_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def find_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, password_hash: str) -> User:
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def username_exists(db: Session, username: str) -> bool:
    return db.query(User.id).filter(User.username == username).first() is not None
