from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.database import Base


class EthVaultTransfer(Base):
    __tablename__ = "eth_vault_transfers"

    __table_args__ = (
        CheckConstraint("amount_wei > 0", name="ck_eth_vault_amount_positive"),
        CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name="ck_eth_vault_risk_score",
        ),
        CheckConstraint(
            "risk_level IS NULL OR risk_level IN "
            "('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_eth_vault_risk_level",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(66), nullable=False, unique=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(36), nullable=False, index=True)
    sender_address = Column(String(42), nullable=False, index=True)
    recipient_address = Column(String(42), nullable=False, index=True)
    amount_wei = Column(Numeric(78, 0), nullable=False)
    chain_id = Column(BigInteger, nullable=False)
    verifying_contract = Column(String(42), nullable=False)

    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String(16), nullable=True)
    decision = Column(String(32), nullable=True)
    status = Column(
        String(32),
        nullable=False,
        default="PENDING_ANALYSIS",
        server_default="PENDING_ANALYSIS",
        index=True,
    )
    requires_auth = Column(Boolean, nullable=False, default=False)
    requires_admin_approval = Column(Boolean, nullable=False, default=False)
    timelock_until = Column(DateTime(timezone=True), nullable=True)
    signature_deadline = Column(DateTime(timezone=True), nullable=True)

    analysis_hash = Column(String(66), nullable=True)
    nonce = Column(String(66), nullable=True, unique=True)
    signature = Column(Text, nullable=True)
    blockchain_tx_hash = Column(String(66), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

