from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class DeviceUserLink(Base):
    __tablename__ = "device_user_links"
    __table_args__ = (
        UniqueConstraint("device_id", "user_id", name="uq_device_user_link"),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        String(255),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_seen = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )