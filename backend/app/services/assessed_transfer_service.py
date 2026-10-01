from sqlalchemy.orm import Session

from app.schemas.final_risk_schema import FinalRiskResult
from app.services.account_service import stage_transfer_with_risk
from app.services.risk_decision_service import assess_final_risk
from app.services.risk_gate_service import ensure_transaction_allowed
from app.services.transaction_risk_engine import calculate_transaction_risk
from app.services.transfer_behavior_service import get_latest_behavior_identity


def execute_assessed_transfer(
    db: Session,
    *,
    user_id: int,
    data,
    risk_result: FinalRiskResult,
):
    """
    서버 내부에서 계산한 최종 위험 평가 결과로 거래를 처리한다.

    거래, RiskAssessment, RiskFactor, 잔액 변경을
    하나의 DB 트랜잭션으로 확정한다.
    """
    if not isinstance(risk_result, FinalRiskResult):
        raise TypeError(
            "서버에서 계산한 FinalRiskResult가 필요합니다."
        )

    try:
        transaction = stage_transfer_with_risk(
            db,
            user_id,
            data,
            risk_result,
        )

        db.commit()
        db.refresh(transaction)

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
    # Keep event writes serialized with scoring and balance mutation.
    ensure_transaction_allowed(db, user_id)
    transaction_risk = calculate_transaction_risk(db, user_id, data)
    behavior_identity = get_latest_behavior_identity(
        db,
        user_id=user_id,
        session_id=str(data.session_id),
    )
    final_risk = assess_final_risk(
        behavior_score=behavior_identity["behavior_score"],
        identity_score=behavior_identity["identity_score"],
        transaction_score=transaction_risk["transaction_score"],
        behavior_reasons=behavior_identity["behavior_reasons"],
        identity_reasons=behavior_identity["identity_reasons"],
        transaction_reasons=transaction_risk["reason_details"],
    )
    return execute_assessed_transfer(
        db,
        user_id=user_id,
        data=data,
        risk_result=final_risk,
    )
