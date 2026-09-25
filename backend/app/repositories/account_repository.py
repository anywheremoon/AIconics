from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account_model import Account


def find_by_user_id(db: Session, user_id: int) -> Account | None:
    return db.query(Account).filter(Account.user_id == user_id).first()


def find_by_account_number(db: Session, account_number: str) -> Account | None:
    return db.query(Account).filter(Account.account_number == account_number).first()


def create_account(
    db: Session,
    user_id: int,
    account_number: str,
    opening_balance: Decimal,
) -> Account:
    account = Account(
        user_id=user_id,
        account_number=account_number,
        balance=opening_balance,
    )
    db.add(account)
    db.flush()
    db.refresh(account)
    return account


def lock_by_ids(db: Session, account_ids: list[int]) -> list[Account]:
    return (
        db.query(Account)
        .filter(Account.id.in_(sorted(account_ids)))
        .order_by(Account.id)
        .with_for_update()
        .all()
    )
