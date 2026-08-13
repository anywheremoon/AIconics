from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    account_number = Column(String(12), nullable=False, unique=True, index=True)
    balance = Column(Numeric(18, 2), nullable=False, default=0)
    opened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
