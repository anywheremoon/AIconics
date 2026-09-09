from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        String(255),
        ForeignKey("devices.device_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ip_address = Column(String(45), nullable=True)
    location = Column(String(255), nullable=True)
    login_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    device_trust_status = Column(String(20), nullable=False)
    repeated_login_detected = Column(Boolean, nullable=False, default=False)
    account_switch_detected = Column(Boolean, nullable=False, default=False)
    recent_login_count = Column(Integer, nullable=False, default=1)
    recent_device_account_count = Column(Integer, nullable=False, default=1)
