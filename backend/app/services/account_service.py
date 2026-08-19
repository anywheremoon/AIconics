import secrets
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account_model import Account
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


def _ensure_request_id_available(db: Session, request_id: str) -> None:
    existing = transaction_repository.find_by_request_id(db, request_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id was already processed",
        )


def list_my_transactions(db: Session, user_id: int):
    account = get_or_create_my_account(db, user_id)
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
    sender = get_or_create_my_account(db, user_id)
    request_id = str(data.request_id)
    _ensure_request_id_available(db, request_id)

    sender = account_repository.lock_by_ids(db, [sender.id])[0]
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
    return transaction
