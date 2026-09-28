import secrets
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account_model import Account
from app.models.event_model import Event
from app.repositories import account_repository, transaction_repository


OPENING_BALANCE = Decimal("100000.00")


def _new_account_number(db: Session) -> str:
    for _ in range(20):
        number = f"{secrets.randbelow(10**12):012d}"
        if account_repository.find_by_account_number(db, number) is None:
            return number
    raise RuntimeError("Could not generate a unique account number")


def create_virtual_account(db: Session, user_id: int):
    existing = account_repository.find_by_user_id(db, user_id)
    if existing is not None:
        return existing
    return account_repository.create_account(
        db,
        user_id,
        _new_account_number(db),
        OPENING_BALANCE,
    )


def get_or_create_my_account(db: Session, user_id: int):
    account = account_repository.find_by_user_id(db, user_id)
    if account is not None:
        return account
    try:
        account = create_virtual_account(db, user_id)
        db.commit()
        db.refresh(account)
        return account
    except IntegrityError:
        db.rollback()
        account = account_repository.find_by_user_id(db, user_id)
        if account is None:
            raise
        return account


def get_my_account(db: Session, user_id: int) -> Account:
    account = account_repository.find_by_user_id(db, user_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


def _ensure_request_id_available(db: Session, request_id: str) -> None:
    existing = transaction_repository.find_by_request_id(db, request_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id was already processed",
        )

def _ensure_transaction_allowed(db: Session, user_id: int) -> None:
    latest_event = (
        db.query(Event)
        .filter(Event.user_id == str(user_id))
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )

    # 아직 Risk 데이터가 없는 사용자는 기존 거래 흐름 유지
    if latest_event is None:
        return

    if latest_event.risk_level in ("MEDIUM", "HIGH"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="현재 위험도가 높아 거래가 제한되었습니다.",
        )

def list_my_transactions(db: Session, user_id: int):
    account = get_my_account(db, user_id)
    transactions = transaction_repository.list_for_account(db, account.id)
    account_numbers = {
        item.id: item.account_number
        for item in db.query(Account).filter(
            Account.id.in_(
                {
                    account_id
                    for transaction in transactions
                    for account_id in (
                        transaction.sender_account_id,
                        transaction.recipient_account_id,
                    )
                    if account_id is not None
                }
            )
        )
    } if transactions else {}
    return [
        {
            "id": transaction.id,
            "request_id": transaction.request_id,
            "transaction_type": transaction.transaction_type,
            "sender_account_id": transaction.sender_account_id,
            "recipient_account_id": transaction.recipient_account_id,
            "sender_account_number": account_numbers.get(transaction.sender_account_id),
            "recipient_account_number": account_numbers.get(transaction.recipient_account_id),
            "amount": transaction.amount,
            "status": transaction.status,
            "created_at": transaction.created_at,
        }
        for transaction in transactions
    ]


def transfer(db: Session, user_id: int, data):
    _ensure_transaction_allowed(db, user_id)
    sender = get_or_create_my_account(db, user_id)
    request_id = str(data.request_id)
    _ensure_request_id_available(db, request_id)

    recipient = account_repository.find_by_account_number(
        db, data.recipient_account_number
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="Recipient account not found")
    if recipient.id == sender.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    locked = {
        account.id: account
        for account in account_repository.lock_by_ids(db, [sender.id, recipient.id])
    }
    sender = locked[sender.id]
    recipient = locked[recipient.id]
    if sender.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    sender.balance -= data.amount
    recipient.balance += data.amount
    transaction = transaction_repository.create_transaction(
        db,
        request_id=request_id,
        transaction_type="TRANSFER",
        sender_account_id=sender.id,
        recipient_account_id=recipient.id,
        amount=data.amount,
    )
    db.commit()
    db.refresh(transaction)
    return transaction


def withdraw(db: Session, user_id: int, data):
    _ensure_transaction_allowed(db, user_id)
    sender = get_my_account(db, user_id)
    request_id = str(data.request_id)
    _ensure_request_id_available(db, request_id)

    locked_accounts = account_repository.lock_by_ids(db, [sender.id])
    if not locked_accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    sender = locked_accounts[0]
    if sender.user_id != user_id:
        raise HTTPException(status_code=403, detail="Account ownership mismatch")
    if sender.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is not active")
    if sender.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    sender.balance -= data.amount
    transaction = transaction_repository.create_transaction(
        db,
        request_id=request_id,
        transaction_type="WITHDRAW",
        sender_account_id=sender.id,
        recipient_account_id=None,
        amount=data.amount,
    )
    db.commit()
    db.refresh(transaction)
    db.refresh(sender)
    return {
        "id": transaction.id,
        "request_id": transaction.request_id,
        "transaction_type": transaction.transaction_type,
        "sender_account_id": transaction.sender_account_id,
        "recipient_account_id": transaction.recipient_account_id,
        "sender_account_number": sender.account_number,
        "recipient_account_number": None,
        "amount": transaction.amount,
        "status": transaction.status,
        "created_at": transaction.created_at,
        "balance_after": sender.balance,
    }