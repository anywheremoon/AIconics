from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.eth_vault_model import EthVaultTransfer


class DuplicateVaultRequestError(ValueError):
    pass


def create_transfer(db: Session, **values) -> EthVaultTransfer:
    transfer = EthVaultTransfer(**values)
    db.add(transfer)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateVaultRequestError(
            "An ETH Vault transfer with this request_id already exists"
        ) from error
    return transfer


def find_by_request_id(
    db: Session,
    request_id: str,
    *,
    for_update: bool = False,
) -> EthVaultTransfer | None:
    query = db.query(EthVaultTransfer).filter(
        EthVaultTransfer.request_id == request_id.lower()
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def find_for_user(
    db: Session, request_id: str, user_id: int
) -> EthVaultTransfer | None:
    return (
        db.query(EthVaultTransfer)
        .filter(
            EthVaultTransfer.request_id == request_id.lower(),
            EthVaultTransfer.user_id == user_id,
        )
        .first()
    )


def list_for_user(
    db: Session, user_id: int, *, limit: int = 100
) -> list[EthVaultTransfer]:
    return (
        db.query(EthVaultTransfer)
        .filter(EthVaultTransfer.user_id == user_id)
        .order_by(EthVaultTransfer.created_at.desc(), EthVaultTransfer.id.desc())
        .limit(limit)
        .all()
    )


def list_admin_pending(
    db: Session, *, limit: int = 100
) -> list[EthVaultTransfer]:
    return (
        db.query(EthVaultTransfer)
        .filter(EthVaultTransfer.status == "ADMIN_REVIEW")
        .order_by(EthVaultTransfer.created_at.asc(), EthVaultTransfer.id.asc())
        .limit(limit)
        .all()
    )


def apply_analysis(db: Session, transfer: EthVaultTransfer, **values):
    for name, value in values.items():
        setattr(transfer, name, value)
    db.flush()
    return transfer


def set_blockchain_submission(
    db: Session, transfer: EthVaultTransfer, transaction_hash: str
):
    transfer.blockchain_tx_hash = transaction_hash
    transfer.status = "RISK_SUBMITTED"
    db.flush()
    return transfer

