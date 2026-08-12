from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    primary_device_id = Column(String(255), nullable=False)
    usual_ip_subnet = Column(String(64), nullable=True)
    usual_location = Column(String(255), nullable=True)
    # Zero means that the baseline is new, not that the user is risky.
    event_count = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
