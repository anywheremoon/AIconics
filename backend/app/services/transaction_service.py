from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import (
    account_repository,
    transaction_repository,
)

TRANSFER = "TRANSFER"
WITHDRAW = "WITHDRAW"

SUCCESS = "SUCCESS"


def _validate_amount(amount: str) -> Decimal:
    value = Decimal(amount)

    if value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than zero",
        )

    return value


def _check_duplicate_request(
    db: Session,
    request_id: str,
):
    transaction = (
        transaction_repository.find_by_request_id(
            db,
            request_id,
        )
    )

    if transaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request",
        )


def get_my_account(
    db: Session,
    user_id: int,
):
    account = account_repository.find_by_user_id(
        db,
        user_id,
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return account


def get_transactions(
    db: Session,
    user_id: int,
):
    account = get_my_account(
        db,
        user_id,
    )

    return transaction_repository.find_by_account_id(
        db,
        account.id,
    )


def transfer(
    db: Session,
    user_id: int,
    request_data,
):
    _check_duplicate_request(
        db,
        request_data.request_id,
    )

    amount = _validate_amount(
        request_data.amount,
    )

    sender = get_my_account(
        db,
        user_id,
    )

    recipient = (
        account_repository.find_by_account_number(
            db,
            request_data.recipient_account_number,
        )
    )

    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient account not found",
        )

    if sender.id == recipient.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same account",
        )

    first_id = min(
        sender.id,
        recipient.id,
    )

    second_id = max(
        sender.id,
        recipient.id,
    )

    first_account = (
        account_repository.find_by_id_for_update(
            db,
            first_id,
        )
    )

    second_account = (
        account_repository.find_by_id_for_update(
            db,
            second_id,
        )
    )

    locked_accounts = {
        first_account.id: first_account,
        second_account.id: second_account,
    }

    sender = locked_accounts[sender.id]
    recipient = locked_accounts[recipient.id]

    if sender.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    try:
        sender.balance -= amount
        recipient.balance += amount

        transaction_repository.create_transaction(
            db,
            {
                "request_id": request_data.request_id,
                "sender_account_id": sender.id,
                "recipient_account_id": recipient.id,
                "transaction_type": TRANSFER,
                "amount": amount,
                "status": SUCCESS,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


def withdraw(
    db: Session,
    user_id: int,
    request_data,
):
    _check_duplicate_request(
        db,
        request_data.request_id,
    )

    amount = _validate_amount(
        request_data.amount,
    )

    account = get_my_account(
        db,
        user_id,
    )

    account = account_repository.find_by_id_for_update(
        db,
        account.id,
    )

    if account.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    try:
        account.balance -= amount

        transaction_repository.create_transaction(
            db,
            {
                "request_id": request_data.request_id,
                "sender_account_id": account.id,
                "recipient_account_id": None,
                "transaction_type": WITHDRAW,
                "amount": amount,
                "status": SUCCESS,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise