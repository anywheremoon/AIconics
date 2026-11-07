from datetime import datetime, timedelta, timezone
from decimal import Decimal

from neo4j.exceptions import ServiceUnavailable
from sqlalchemy.orm import Session

from app.repositories import eth_vault_repository
from app.schemas.eth_vault_schema import EthVaultAnalyzeRequest
from app.services import graph_risk_engine
from app.services.eth_vault_signature_service import (
    build_analysis_hash,
    build_signed_result,
    new_nonce,
    sign_result,
)
from app.services.risk_decision_service import assess_final_risk
from app.services.transfer_behavior_service import get_latest_behavior_identity


SIGNATURE_TTL_SECONDS = 300
HIGH_VALUE_WEI = 10**18
VERY_HIGH_VALUE_WEI = 10 * 10**18
POLICIES = {
    "LOW": {
        "status": "READY",
        "requires_auth": False,
        "requires_admin_approval": False,
        "timelock_seconds": 0,
    },
    "MEDIUM": {
        "status": "AUTH_REQUIRED",
        "requires_auth": True,
        "requires_admin_approval": False,
        "timelock_seconds": 0,
    },
    "HIGH": {
        "status": "ADMIN_REVIEW",
        "requires_auth": True,
        "requires_admin_approval": True,
        "timelock_seconds": 3600,
    },
    "CRITICAL": {
        "status": "REJECTED",
        "requires_auth": True,
        "requires_admin_approval": True,
        "timelock_seconds": 0,
    },
}


def policy_for_risk(*, risk_score: int, risk_level: str, decision: str) -> dict:
    try:
        policy = POLICIES[risk_level]
    except KeyError as error:
        raise ValueError(f"Unsupported ETH Vault risk level: {risk_level}") from error
    return {
        "risk_score": int(risk_score),
        "risk_level": risk_level,
        "decision": decision,
        **policy,
    }


def _transaction_risk(db: Session, *, user_id: int, data) -> dict:
    amount = int(data.amount_wei)
    previous_recipient = (
        db.query(eth_vault_repository.EthVaultTransfer.id)
        .filter(
            eth_vault_repository.EthVaultTransfer.user_id == user_id,
            eth_vault_repository.EthVaultTransfer.recipient_address
            == data.recipient_address.lower(),
        )
        .first()
    )
    score = 0
    reasons = []

    if previous_recipient is None:
        score += 15
        reasons.append(
            {
                "reason_code": "ETH_VAULT_NEW_RECIPIENT",
                "description": "This is a new ETH recipient for the user.",
                "score_type": "TRANSACTION",
                "score_contribution": 15,
            }
        )
    if amount >= VERY_HIGH_VALUE_WEI:
        score += 55
        reasons.append(
            {
                "reason_code": "ETH_VAULT_VERY_HIGH_AMOUNT",
                "description": "The transfer is at least 10 ETH.",
                "score_type": "TRANSACTION",
                "score_contribution": 55,
            }
        )
    elif amount >= HIGH_VALUE_WEI:
        score += 30
        reasons.append(
            {
                "reason_code": "ETH_VAULT_HIGH_AMOUNT",
                "description": "The transfer is at least 1 ETH.",
                "score_type": "TRANSACTION",
                "score_contribution": 30,
            }
        )
    return {"transaction_score": min(score, 100), "reason_details": reasons}


def _risk_result(db: Session, *, user_id: int, data):
    behavior_identity = get_latest_behavior_identity(
        db, user_id=user_id, session_id=str(data.session_id)
    )
    transaction = _transaction_risk(db, user_id=user_id, data=data)
    try:
        graph = graph_risk_engine.analyze_graph_risk(user_id)
    except ServiceUnavailable:
        graph = {"graph_score": None, "reason_details": []}

    return assess_final_risk(
        behavior_score=behavior_identity["behavior_score"],
        identity_score=behavior_identity["identity_score"],
        transaction_score=transaction["transaction_score"],
        graph_score=graph["graph_score"],
        behavior_reasons=behavior_identity["behavior_reasons"],
        identity_reasons=behavior_identity["identity_reasons"],
        transaction_reasons=transaction["reason_details"],
        graph_reasons=graph["reason_details"],
        transaction_maximum=70.0,
        graph_maximum=45.0,
    )


def analyze_transfer(
    db: Session,
    *,
    user_id: int,
    data: EthVaultAnalyzeRequest,
    now: datetime | None = None,
    private_key: str | None = None,
) -> dict:
    analysis_time = now or datetime.now(timezone.utc)
    if analysis_time.tzinfo is None:
        analysis_time = analysis_time.replace(tzinfo=timezone.utc)

    if eth_vault_repository.find_by_request_id(db, data.request_id):
        raise eth_vault_repository.DuplicateVaultRequestError(
            "An ETH Vault transfer with this request_id already exists"
        )

    result = _risk_result(db, user_id=user_id, data=data)
    policy = policy_for_risk(
        risk_score=round(result.final_risk_score),
        risk_level=result.risk_level,
        decision=result.decision,
    )
    timelock_until = (
        analysis_time + timedelta(seconds=policy["timelock_seconds"])
        if policy["timelock_seconds"]
        else None
    )
    deadline = analysis_time + timedelta(seconds=SIGNATURE_TTL_SECONDS)
    reasons = [reason.model_dump(mode="json") for reason in result.reasons]
    analysis_hash = build_analysis_hash(
        request_id=data.request_id,
        risk_score=policy["risk_score"],
        risk_level=policy["risk_level"],
        decision=policy["decision"],
        reasons=reasons,
    )
    nonce = new_nonce()
    signed_result = build_signed_result(
        request_id=data.request_id,
        sender_address=data.sender_address,
        recipient_address=data.recipient_address,
        amount_wei=data.amount_wei,
        risk_score=policy["risk_score"],
        risk_level=policy["risk_level"],
        requires_auth=policy["requires_auth"],
        requires_admin_approval=policy["requires_admin_approval"],
        timelock_until=timelock_until,
        deadline=deadline,
        analysis_hash=analysis_hash,
        nonce=nonce,
    )
    signature = sign_result(
        signed_result,
        chain_id=data.chain_id,
        verifying_contract=data.verifying_contract,
        private_key=private_key,
    )

    transfer = eth_vault_repository.create_transfer(
        db,
        request_id=data.request_id.lower(),
        user_id=user_id,
        session_id=str(data.session_id),
        sender_address=data.sender_address.lower(),
        recipient_address=data.recipient_address.lower(),
        amount_wei=Decimal(data.amount_wei),
        chain_id=data.chain_id,
        verifying_contract=data.verifying_contract.lower(),
        risk_score=policy["risk_score"],
        risk_level=policy["risk_level"],
        decision=policy["decision"],
        status=policy["status"],
        requires_auth=policy["requires_auth"],
        requires_admin_approval=policy["requires_admin_approval"],
        timelock_until=timelock_until,
        signature_deadline=deadline,
        analysis_hash=analysis_hash,
        nonce=nonce,
        signature=signature,
    )
    try:
        db.commit()
        db.refresh(transfer)
    except Exception:
        db.rollback()
        raise

    return {
        "transfer": transfer,
        "policy": policy,
        "signed_result": signed_result,
        "signature": signature,
    }

