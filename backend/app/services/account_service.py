import secrets
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.graph_sync_service import sync_transfer
from app.models.account_model import Account
from app.models.event_model import Event
from app.repositories import account_repository, transaction_repository
from app.schemas.final_risk_schema import FinalRiskResult
from app.services.risk_assessment_service import create_risk_assessment
from app.services.risk_decision_service import (
    decide_risk,
    transaction_status_for_decision,
)


OPENING_BALANCE = Decimal("100000.00")
TRANSACTION_BLOCKED_RISK_LEVELS = frozenset({"MEDIUM", "HIGH"})
TRANSACTION_BLOCKED_RISK_SCORE = 40


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


def _ensure_request_id_available(
    db: Session,
    request_id: str,
) -> None:
    existing = transaction_repository.find_by_request_id(
        db,
        request_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id was already processed",
        )



def _ensure_transaction_allowed(
    db: Session,
    user_id: int,
) -> None:
    """Block a transaction when the latest risk is medium or high."""

    latest_event = (
        db.query(Event)
        .filter(Event.user_id == str(user_id))
        .order_by(
            Event.created_at.desc(),
            Event.id.desc(),
        )
        .first()
    )

    if latest_event is None:
        return

    risk_level = (latest_event.risk_level or "").upper()
    risk_score = float(latest_event.risk_score or 0)

    if (
        risk_level in TRANSACTION_BLOCKED_RISK_LEVELS
        or risk_score >= TRANSACTION_BLOCKED_RISK_SCORE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transaction blocked due to current risk level",
        )


def list_my_transactions(db: Session, user_id: int):
    account = get_my_account(db, user_id)

    transactions = transaction_repository.list_for_account(
        db,
        account.id,
    )

    account_ids = {
        account_id
        for transaction in transactions
        for account_id in (
            transaction.sender_account_id,
            transaction.recipient_account_id,
        )
        if account_id is not None
    }

    account_numbers = (
        {
            item.id: item.account_number
            for item in db.query(Account).filter(
                Account.id.in_(account_ids)
            )
        }
        if account_ids
        else {}
    )

    return [
        {
            "id": transaction.id,
            "request_id": transaction.request_id,
            "transaction_type": transaction.transaction_type,
            "sender_account_id": transaction.sender_account_id,
            "recipient_account_id": transaction.recipient_account_id,
            "sender_account_number": account_numbers.get(
                transaction.sender_account_id
            ),
            "recipient_account_number": account_numbers.get(
                transaction.recipient_account_id
            ),
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
        db,
        data.recipient_account_number,
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient account not found",
        )

    if recipient.id == sender.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer to the same account",
        )

    locked = {
        account.id: account
        for account in account_repository.lock_by_ids(
            db,
            [sender.id, recipient.id],
        )
    }

    sender = locked[sender.id]
    recipient = locked[recipient.id]

    if sender.balance < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance",
        )

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

    sync_transfer(
        transaction,
        sender,
        recipient,
    )
    return transaction


def withdraw(db: Session, user_id: int, data):
    _ensure_transaction_allowed(db, user_id)

    sender = get_my_account(db, user_id)
    request_id = str(data.request_id)

    _ensure_request_id_available(db, request_id)

    locked_accounts = account_repository.lock_by_ids(
        db,
        [sender.id],
    )

    if not locked_accounts:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    sender = locked_accounts[0]

    if sender.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Account ownership mismatch",
        )

    if sender.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Account is not active",
        )

    if sender.balance < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance",
        )

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



def stage_transfer_with_risk(
    db: Session,
    user_id: int,
    data,
    risk_result: FinalRiskResult,
):
    """
    백엔드 내부에서 계산한 위험 평가 결과로 이체를 준비한다.

    APPROVED일 때만 잔액을 변경한다.
    거래, 평가, 잔액 변경은 같은 DB 트랜잭션에 남긴다.
    이 함수는 commit하지 않는다. 호출자가 commit 또는 rollback한다.
    """
    if not isinstance(risk_result, FinalRiskResult):
        raise TypeError(
            "risk_result는 FinalRiskResult여야 합니다."
        )

    # 외부에서 전달된 결과가 잘못 조합되었더라도
    # 고위험 점수가 APPROVED로 처리되지 않도록 검사
    expected_decision = decide_risk(
        risk_result.final_risk_score
    )["decision"]

    if risk_result.decision != expected_decision:
        raise ValueError(
            "최종 점수와 거래 결정이 일치하지 않습니다."
        )

    _ensure_transaction_allowed(db, user_id)

    sender = get_my_account(db, user_id)
    request_id = str(data.request_id)

    _ensure_request_id_available(db, request_id)

    recipient = account_repository.find_by_account_number(
        db,
        data.recipient_account_number,
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient account not found",
        )

    if recipient.id == sender.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer to the same account",
        )

    # 송신·수신 계좌를 같은 순서로 잠금
    locked = {
        account.id: account
        for account in account_repository.lock_by_ids(
            db,
            [sender.id, recipient.id],
        )
    }

    if sender.id not in locked or recipient.id not in locked:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    sender = locked[sender.id]
    recipient = locked[recipient.id]

    if sender.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Account ownership mismatch",
        )

    if sender.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Account is not active",
        )

    if recipient.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Recipient account is not active",
        )

    if sender.balance < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance",
        )

    transaction_status = transaction_status_for_decision(
        risk_result.decision
    )

    transaction = transaction_repository.create_transaction(
        db,
        request_id=request_id,
        transaction_type="TRANSFER",
        sender_account_id=sender.id,
        recipient_account_id=recipient.id,
        amount=data.amount,
        status=transaction_status,
    )

    create_risk_assessment(
        db,
        transaction_id=transaction.id,
        result=risk_result,
    )

    if risk_result.decision == "APPROVED":
        sender.balance -= data.amount
        recipient.balance += data.amount

    db.flush()

    return transaction

