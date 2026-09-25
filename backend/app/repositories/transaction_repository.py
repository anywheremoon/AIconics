from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.transaction_model import Transaction


def find_by_request_id(db: Session, request_id: str) -> Transaction | None:
    return db.query(Transaction).filter(Transaction.request_id == request_id).first()


def list_for_account(db: Session, account_id: int) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(
            or_(
                Transaction.sender_account_id == account_id,
                Transaction.recipient_account_id == account_id,
            )
        )
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .all()
    )


def create_transaction(
    db: Session,
    *,
    request_id: str,
    transaction_type: str,
    sender_account_id: int,
    recipient_account_id: int | None,
    amount: Decimal,
) -> Transaction:
    transaction = Transaction(
        request_id=request_id,
        transaction_type=transaction_type,
        sender_account_id=sender_account_id,
        recipient_account_id=recipient_account_id,
        amount=amount,
        status="COMPLETED",
    )
    db.add(transaction)
    db.flush()
    db.refresh(transaction)
    return transaction
