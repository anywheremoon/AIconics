from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    text,
    true,
)
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

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    logout_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Existing sessions are treated as fully authenticated.  New login
    # attempts explicitly set this to AUTHENTICATED, REQUIRE_VERIFICATION,
    # or PENDING before a token is issued.
    auth_status = Column(
        String(24),
        nullable=False,
        default="AUTHENTICATED",
        server_default="AUTHENTICATED",
        index=True,
    )
    auth_reason_codes = Column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )

    verification_code_hash = Column(String(64), nullable=True)
    verification_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_requested_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    device_trust_status = Column(String(20), nullable=False)
    repeated_login_detected = Column(
        Boolean, nullable=False, default=False
    )
    account_switch_detected = Column(
        Boolean, nullable=False, default=False
    )
    recent_login_count = Column(
        Integer, nullable=False, default=1
    )
    recent_device_account_count = Column(
        Integer, nullable=False, default=1
    )