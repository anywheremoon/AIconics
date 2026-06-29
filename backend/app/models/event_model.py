from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Event(Base):
    __tablename__ = "behavior_events"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    location = Column(String, nullable=True)

    typing_speed = Column(Float, nullable=False)
    mouse_move_count = Column(Integer, nullable=False)
    click_count = Column(Integer, nullable=False)
    is_new_device = Column(Boolean, default=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )