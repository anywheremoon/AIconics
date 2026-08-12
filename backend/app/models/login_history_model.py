from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class LoginHistory(Base):
    __tablename__ = "login_histories"

    id = Column(Integer, primary_key=True, index=True)
    # A failed attempt for an unknown username has no user to reference.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    login_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    success = Column(Boolean, nullable=False, default=False)
