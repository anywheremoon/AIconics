from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    primary_device_id = Column(String(255), nullable=True)
    usual_ip_subnet = Column(String(64), nullable=True)
    usual_location = Column(String(255), nullable=True)

    # Running averages used as the user's normal behavior baseline.
    avg_typing_speed = Column(Float, nullable=True)
    avg_hold_time = Column(Float, nullable=True)
    avg_flight_time = Column(Float, nullable=True)
    avg_mouse_move_count = Column(Float, nullable=True)
    avg_click_count = Column(Float, nullable=True)

    # Zero means that the baseline is new, not that the user is risky.
    event_count = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
