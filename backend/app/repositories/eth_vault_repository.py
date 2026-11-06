import os
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.eth_vault_model import EthVaultTransfer


class DuplicateVaultRequestError(ValueError):
    pass


def current_scope():
    deployment_id = os.getenv(
        "ETH_VAULT_DEPLOYMENT_ID", ""
    ).strip()
    address = os.getenv(
        "ETH_VAULT_CONTRACT_ADDRESS", ""
    ).strip().lower()
    chain_id = int(os.getenv("BLOCKCHAIN_CHAIN_ID", "31337"))

    if not deployment_id or not address:
        raise RuntimeError("ETH Vault deployment is not configured")

    deployment_id = str(UUID(deployment_id))
    return deployment_id, chain_id, address


def scoped_query(db: Session):
    deployment_id, chain_id, address = current_scope()
    return db.query(EthVaultTransfer).filter(
        EthVaultTransfer.deployment_id == deployment_id,
        EthVaultTransfer.chain_id == chain_id,
        EthVaultTransfer.verifying_contract == address,
    )


def create_transfer(db: Session, **values) -> EthVaultTransfer:
    deployment_id, chain_id, address = current_scope()

    if (
        int(values["chain_id"]) != chain_id
        or values["verifying_contract"].lower() != address
    ):
        raise ValueError("Configured ETH Vault deployment mismatch")

    values["deployment_id"] = deployment_id
    values["verifying_contract"] = address
    values["request_id"] = values["request_id"].lower()

    transfer = EthVaultTransfer(**values)
    db.add(transfer)

    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        constraint = getattr(
            getattr(error.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint in {
            "uq_eth_vault_deployment_request",
            "ix_eth_vault_transfers_request_id",
            "eth_vault_transfers_request_id_key",
        }:
            raise DuplicateVaultRequestError(
                "An ETH Vault transfer with this request_id already exists"
            ) from error
        raise

    return transfer


def find_by_request_id(
    db: Session,
    request_id: str,
    *,
    for_update: bool = False,
) -> EthVaultTransfer | None:
    query = scoped_query(db).filter(
        EthVaultTransfer.request_id == request_id.lower()
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def find_for_user(
    db: Session, request_id: str, user_id: int
) -> EthVaultTransfer | None:
    return (
        scoped_query(db)
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
        scoped_query(db)
        .filter(EthVaultTransfer.user_id == user_id)
        .order_by(
            EthVaultTransfer.created_at.desc(),
            EthVaultTransfer.id.desc(),
        )
        .limit(limit)
        .all()
    )


def list_admin_pending(
    db: Session, *, limit: int = 100
) -> list[EthVaultTransfer]:
    return (
        scoped_query(db)
        .filter(
            EthVaultTransfer.risk_level == "HIGH",
            EthVaultTransfer.requires_admin_approval.is_(True),
            EthVaultTransfer.status.in_(
                ["ADMIN_REVIEW", "RISK_SUBMITTED"]
            ),
        )
        .order_by(
            EthVaultTransfer.created_at.asc(),
            EthVaultTransfer.id.asc(),
        )
        .limit(limit)
        .all()
    )


def apply_analysis(db: Session, transfer: EthVaultTransfer, **values):
    for name, value in values.items():
        setattr(transfer, name, value)
    db.flush()
    return transfer


def set_blockchain_submission(
    db: Session,
    transfer: EthVaultTransfer,
    transaction_hash: str,
):
    transfer.blockchain_tx_hash = transaction_hash
    transfer.status = "RISK_SUBMITTED"
    db.flush()
    return transfer
