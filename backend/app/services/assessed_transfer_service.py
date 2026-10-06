from neo4j.exceptions import ServiceUnavailable
from sqlalchemy.orm import Session

from app.models.account_model import Account
from app.schemas.final_risk_schema import FinalRiskResult
from app.services.account_service import stage_transfer_with_risk
from app.services.graph_sync_service import sync_transfer
from app.services.risk_decision_service import assess_final_risk
from app.services.risk_gate_service import ensure_transaction_allowed
from app.services.session_service import validate_active_session
from app.services.transaction_risk_engine import calculate_transaction_risk
from app.services.transfer_behavior_service import get_latest_behavior_identity
from app.services import graph_risk_engine


def execute_assessed_transfer(
    db: Session,
    *,
    user_id: int,
    data,
    risk_result: FinalRiskResult,
):
    """
    거래, 위험 평가, 잔액 변경을 하나의 DB 트랜잭션으로 확정한다.
    """
    if not isinstance(risk_result, FinalRiskResult):
        raise TypeError(
            "서버에서 계산한 FinalRiskResult가 필요합니다."
        )

    try:
        # 이 함수를 직접 호출하는 경우에도 종료된 세션을 거절한다.
        validate_active_session(
            db,
            session_id=str(data.session_id),
            user_id=user_id,
        )

        transaction = stage_transfer_with_risk(
            db,
            user_id,
            data,
            risk_result,
        )

        db.commit()
        db.refresh(transaction)

        # Only completed transfers are facts in the transaction graph.
        # Pending/review transactions must not influence later graph scores.
        if transaction.status == "COMPLETED":
            sender = db.get(Account, transaction.sender_account_id)
            recipient = db.get(Account, transaction.recipient_account_id)
            if sender is not None and recipient is not None:
                sync_transfer(transaction, sender, recipient)

        return transaction

    except Exception:
        db.rollback()
        raise


def assess_and_execute_transfer(
    db: Session,
    *,
    user_id: int,
    data,
):
    """Calculate all risk domains and atomically persist the transfer decision."""
    try:
        # Keep event writes serialized with scoring and balance mutation.
        ensure_transaction_allowed(db, user_id)

        transaction_risk = calculate_transaction_risk(db, user_id, data)
        behavior_identity = get_latest_behavior_identity(
            db,
            user_id=user_id,
            session_id=str(data.session_id),
        )

        try:
            graph_risk = graph_risk_engine.analyze_graph_risk(user_id)
        except ServiceUnavailable:
            # Neo4j is optional. A missing graph score selects the calibrated
            # three-domain policy instead of treating an outage as zero risk.
            graph_risk = {
                "graph_score": None,
                "reason_details": [],
            }

        final_risk = assess_final_risk(
            behavior_score=behavior_identity["behavior_score"],
            identity_score=behavior_identity["identity_score"],
            transaction_score=transaction_risk["transaction_score"],
            graph_score=graph_risk["graph_score"],
            behavior_reasons=behavior_identity["behavior_reasons"],
            identity_reasons=behavior_identity["identity_reasons"],
            transaction_reasons=transaction_risk["reason_details"],
            graph_reasons=graph_risk["reason_details"],
        )

        return execute_assessed_transfer(
            db,
            user_id=user_id,
            data=data,
            risk_result=final_risk,
        )

    except Exception:
        db.rollback()
        raise
