from sqlalchemy.orm import Session

from app.schemas.final_risk_schema import FinalRiskResult
from app.services.account_service import stage_transfer_with_risk


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