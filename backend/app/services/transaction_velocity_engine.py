from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction_model import Transaction


HIGH_FREQUENCY_WINDOW = timedelta(minutes=10)
HIGH_FREQUENCY_COUNT = 5
HIGH_AMOUNT_WINDOW = timedelta(hours=1)
HIGH_AMOUNT_THRESHOLD = Decimal("10000000.00")
RECENT_INCOMING_WINDOW = timedelta(minutes=10)
BALANCE_DRAIN_RATIO = Decimal("0.80")

VELOCITY_HIGH_FREQUENCY_SCORE = 20
VELOCITY_HIGH_AMOUNT_SCORE = 25
RAPID_BALANCE_DRAIN_SCORE = 25


def calculate_transaction_velocity(
    db: Session,
    sender_account_id: int,
    amount: Decimal,
    account_balance: Decimal,
    *,
    now: datetime,
) -> dict:
    """Calculate outgoing transfer velocity including the proposed transfer."""
    common_filters = (
        Transaction.sender_account_id == sender_account_id,
        Transaction.transaction_type == "TRANSFER",
        Transaction.status == "COMPLETED",
    )

    recent_count = (
        db.query(func.count(Transaction.id))
        .filter(
            *common_filters,
            Transaction.created_at >= now - HIGH_FREQUENCY_WINDOW,
        )
        .scalar()
        or 0
    )
    recent_amount = (
        db.query(func.sum(Transaction.amount))
        .filter(
            *common_filters,
            Transaction.created_at >= now - HIGH_AMOUNT_WINDOW,
        )
        .scalar()
        or Decimal("0.00")
    )
    recent_amount = Decimal(str(recent_amount))
    recent_incoming_amount = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.recipient_account_id == sender_account_id,
            Transaction.transaction_type == "TRANSFER",
            Transaction.status == "COMPLETED",
            Transaction.created_at >= now - RECENT_INCOMING_WINDOW,
        )
        .scalar()
        or Decimal("0.00")
    )
    recent_incoming_amount = Decimal(str(recent_incoming_amount))

    projected_count = int(recent_count) + 1
    projected_amount = recent_amount + amount
    is_rapid_balance_drain = (
        recent_incoming_amount > 0
        and account_balance > 0
        and amount >= account_balance * BALANCE_DRAIN_RATIO
    )
    reasons = []
    score = 0

    if projected_count >= HIGH_FREQUENCY_COUNT:
        reasons.append("VELOCITY_HIGH_FREQUENCY")
        score += VELOCITY_HIGH_FREQUENCY_SCORE

    if projected_amount > HIGH_AMOUNT_THRESHOLD:
        reasons.append("VELOCITY_HIGH_AMOUNT")
        score += VELOCITY_HIGH_AMOUNT_SCORE

    if is_rapid_balance_drain:
        reasons.append("RAPID_BALANCE_DRAIN")
        score += RAPID_BALANCE_DRAIN_SCORE

    return {
        "velocity_score": score,
        "recent_10_minute_count": int(recent_count),
        "projected_10_minute_count": projected_count,
        "recent_1_hour_amount": recent_amount,
        "projected_1_hour_amount": projected_amount,
        "recent_incoming_amount": recent_incoming_amount,
        "is_rapid_balance_drain": is_rapid_balance_drain,
        "reasons": reasons,
    }
