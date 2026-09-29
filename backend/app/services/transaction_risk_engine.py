from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction_model import Transaction
from app.repositories import account_repository, user_session_repository
from app.services.transaction_velocity_engine import calculate_transaction_velocity


NEW_ACCOUNT_SCORE = 20
NEW_RECIPIENT_SCORE = 15
SHORTLY_AFTER_LOGIN_SCORE = 10
HIGH_AMOUNT_SCORE = 30
UNUSUALLY_LARGE_AMOUNT_SCORE = 20
NEW_ACCOUNT_HIGH_AMOUNT_SCORE = 10

NEW_ACCOUNT_MAX_AGE_DAYS = 1
SHORTLY_AFTER_LOGIN_MAX_MINUTES = 5
HIGH_AMOUNT_THRESHOLD = Decimal("5000000.00")
UNUSUAL_AMOUNT_MULTIPLIER = Decimal("3")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _has_transferred_to_recipient(
    db: Session,
    sender_account_id: int,
    recipient_account_id: int,
) -> bool:
    return (
        db.query(Transaction.id)
        .filter(
            Transaction.sender_account_id == sender_account_id,
            Transaction.recipient_account_id == recipient_account_id,
            Transaction.transaction_type == "TRANSFER",
            Transaction.status == "COMPLETED",
        )
        .first()
        is not None
    )


def _average_transfer_amount(db: Session, sender_account_id: int) -> Decimal | None:
    average = (
        db.query(func.avg(Transaction.amount))
        .filter(
            Transaction.sender_account_id == sender_account_id,
            Transaction.transaction_type == "TRANSFER",
            Transaction.status == "COMPLETED",
        )
        .scalar()
    )
    return None if average is None else Decimal(str(average))


def calculate_transaction_risk(
    db: Session,
    user_id: int,
    data,
    *,
    now: datetime | None = None,
) -> dict:
    """Score a proposed transfer without creating or executing it."""
    scoring_time = _utc(now or datetime.now(timezone.utc))
    amount = Decimal(str(data.amount))

    sender = account_repository.find_by_user_id(db, user_id)
    if sender is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender account not found",
        )

    recipient = account_repository.find_by_account_number(
        db,
        data.recipient_account_number,
    )
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient account not found",
        )
    if recipient.id == sender.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assess a transfer to the same account",
        )

    user_session = user_session_repository.find_by_id(db, str(data.session_id))
    if user_session is None or user_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to the authenticated user",
        )

    account_age_seconds = max(
        (scoring_time - _utc(sender.opened_at)).total_seconds(),
        0,
    )
    account_age_days = int(account_age_seconds // 86400)
    minutes_after_login = max(
        (scoring_time - _utc(user_session.login_at)).total_seconds() / 60,
        0,
    )

    is_new_recipient = not _has_transferred_to_recipient(
        db,
        sender.id,
        recipient.id,
    )
    average_transfer_amount = _average_transfer_amount(db, sender.id)
    is_high_amount = amount >= HIGH_AMOUNT_THRESHOLD
    is_new_account_high_amount = (
        account_age_days <= NEW_ACCOUNT_MAX_AGE_DAYS and is_high_amount
    )
    is_unusually_large = (
        average_transfer_amount is not None
        and amount >= average_transfer_amount * UNUSUAL_AMOUNT_MULTIPLIER
    )

    score = 0
    reasons = []

    if account_age_days <= NEW_ACCOUNT_MAX_AGE_DAYS:
        score += NEW_ACCOUNT_SCORE
        reasons.append("NEW_ACCOUNT")

    if is_new_recipient:
        score += NEW_RECIPIENT_SCORE
        reasons.append("NEW_RECIPIENT")

    if minutes_after_login <= SHORTLY_AFTER_LOGIN_MAX_MINUTES:
        score += SHORTLY_AFTER_LOGIN_SCORE
        reasons.append("TRANSFER_SHORTLY_AFTER_LOGIN")

    if is_high_amount:
        score += HIGH_AMOUNT_SCORE
        reasons.append("HIGH_AMOUNT_TRANSFER")

    if is_unusually_large:
        score += UNUSUALLY_LARGE_AMOUNT_SCORE
        reasons.append("UNUSUALLY_LARGE_TRANSFER")

    if is_new_account_high_amount:
        score += NEW_ACCOUNT_HIGH_AMOUNT_SCORE
        reasons.append("NEW_ACCOUNT_HIGH_AMOUNT")

    velocity = calculate_transaction_velocity(
        db,
        sender.id,
        amount,
        Decimal(str(sender.balance)),
        now=scoring_time,
    )
    score += velocity["velocity_score"]
    reasons.extend(velocity["reasons"])

    return {
        "transaction_score": min(max(score, 0), 100),
        "is_new_recipient": is_new_recipient,
        "account_age_days": account_age_days,
        "minutes_after_login": round(minutes_after_login, 2),
        "is_high_amount": is_high_amount,
        "is_unusually_large": is_unusually_large,
        "is_new_account_high_amount": is_new_account_high_amount,
        "is_rapid_balance_drain": velocity["is_rapid_balance_drain"],
        "average_transfer_amount": average_transfer_amount,
        "recent_10_minute_count": velocity["recent_10_minute_count"],
        "projected_10_minute_count": velocity["projected_10_minute_count"],
        "recent_1_hour_amount": velocity["recent_1_hour_amount"],
        "projected_1_hour_amount": velocity["projected_1_hour_amount"],
        "recent_incoming_amount": velocity["recent_incoming_amount"],
        "reasons": reasons,
    }
