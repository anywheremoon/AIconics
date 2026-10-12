from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account_model import Account
from app.models.transaction_model import Transaction
from app.models.risk_assessment_model import RiskAssessment
from app.models.risk_factor_model import RiskFactor
from app.schemas.risk_assessment_schema import (
    RiskAssessmentResponse,
)
from app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api/risk-assessments",
    tags=["Risk Assessments"],
)


@router.get(
    "/{transaction_id}",
    response_model=RiskAssessmentResponse,
)
def read_risk_assessment(
    transaction_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 이 거래의 송신 계좌가 로그인 사용자 소유인지 확인
    transaction = (
        db.query(Transaction)
        .join(
            Account,
            Account.id == Transaction.sender_account_id,
        )
        .filter(
            Transaction.id == transaction_id,
            Account.user_id == current_user.id,
        )
        .first()
    )

    if transaction is None:
        # 다른 사람의 거래 ID 존재 여부도 알려주지 않음
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    # 재평가가 있었다면 가장 최근 평가를 반환
    assessment = (
        db.query(RiskAssessment)
        .filter(
            RiskAssessment.transaction_id
            == transaction.id
        )
        .order_by(
            RiskAssessment.created_at.desc(),
            RiskAssessment.id.desc(),
        )
        .first()
    )

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Risk assessment not found",
        )

    factors = (
        db.query(RiskFactor)
        .filter(
            RiskFactor.risk_assessment_id
            == assessment.id
        )
        .order_by(RiskFactor.id.asc())
        .all()
    )

    return {
        "id": assessment.id,
        "transaction_id": assessment.transaction_id,
        "behavior_score": assessment.behavior_score,
        "identity_score": assessment.identity_score,
        "transaction_score": assessment.transaction_score,
        "graph_score": assessment.graph_score,
        "final_risk_score": assessment.final_risk_score,
        "risk_level": assessment.risk_level,
        "decision": assessment.decision,
        "policy_version": assessment.policy_version,
        "calculation_details": (
            assessment.calculation_details
        ),
        "created_at": assessment.created_at,
        "factors": factors,
    }