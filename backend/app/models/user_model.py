from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    # Nullable for accounts created before email verification was introduced.
    # All new registrations require an email address at the API boundary.
    email = Column(String(254), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(10),
        nullable=False,
        default="USER",
        server_default="USER",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
