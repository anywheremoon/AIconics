from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.sql import func

from app.database import Base
from app.models.device_model import Device  # noqa: F401
from app.models.device_user_link_model import DeviceUserLink  # noqa: F401
from app.models.user_session_model import UserSession  # noqa: F401


class Event(Base):
    __tablename__ = "behavior_events"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String, nullable=False, index=True)

    session_id = Column(
        String(36),
        ForeignKey("user_sessions.session_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    device_id = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    location = Column(String, nullable=True)

    typing_speed = Column(Float, nullable=False)
    avg_hold_time = Column(Float, nullable=False)
    avg_flight_time = Column(Float, nullable=False)
    total_keystrokes = Column(Integer, nullable=False)

    mouse_move_count = Column(Integer, nullable=False)
    click_count = Column(Integer, nullable=False)

    is_new_device = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    profile_deviation_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    detect_anomaly = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    behavior_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    identity_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    baseline_status = Column(
        String,
        nullable=False,
        default="INSUFFICIENT_DATA",
    )

    reasons = Column(
        JSON,
        nullable=False,
        default=list,
    )

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )