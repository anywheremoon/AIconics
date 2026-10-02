from sqlalchemy.orm import Session

from app.models.risk_assessment_model import RiskAssessment
from app.models.risk_factor_model import RiskFactor
from app.schemas.final_risk_schema import FinalRiskResult
from app.services.score_combiner import (
    BEHAVIOR_RAW_MAX,
    BEHAVIOR_WEIGHT,
    IDENTITY_RAW_MAX,
    IDENTITY_WEIGHT,
    TRANSACTION_WEIGHT,
)


POLICY_VERSION = "weighted_rules_v1"


def create_risk_assessment(
    db: Session,
    *,
    transaction_id: int,
    result: FinalRiskResult,
) -> RiskAssessment:
    """
    계산이 끝난 위험 평가를 DB에 저장한다.

    이 함수는 flush만 수행한다.
    거래 상태와 잔액 처리까지 마친 호출자가 commit한다.
    """

    if (
        not isinstance(transaction_id, int)
        or isinstance(transaction_id, bool)
        or transaction_id <= 0
    ):
        raise ValueError("유효한 transaction_id가 필요합니다.")

    if not isinstance(result, FinalRiskResult):
        raise TypeError(
            "result는 FinalRiskResult여야 합니다."
        )

    assessment = RiskAssessment(
        transaction_id=transaction_id,
        behavior_score=result.behavior_score,
        identity_score=result.identity_score,
        transaction_score=result.transaction_score,
        graph_score=result.graph_score,
        final_risk_score=result.final_risk_score,
        risk_level=result.risk_level,
        decision=result.decision,
        policy_version=POLICY_VERSION,
        calculation_details={
            "weights": {
                "behavior": BEHAVIOR_WEIGHT,
                "identity": IDENTITY_WEIGHT,
                "transaction": TRANSACTION_WEIGHT,
            },
            "normalization_maxima": {
                "behavior": BEHAVIOR_RAW_MAX,
                "identity": IDENTITY_RAW_MAX,
            },
            "normalized_behavior_score": (
                result.normalized_behavior_score
            ),
            "normalized_identity_score": (
                result.normalized_identity_score
            ),
            "weighted_contributions": (
                result.weighted_contributions.model_dump()
            ),
            # 현재 공식은 Graph 점수를 저장하지만
            # 최종 점수에는 포함하지 않음
            "graph_included_in_final_score": False,
        },
    )

    db.add(assessment)
    db.flush()  # assessment.id를 얻기 위해 flush

    for reason in result.reasons:
        db.add(
            RiskFactor(
                risk_assessment_id=assessment.id,
                reason_code=reason.reason_code,
                description=reason.description,
                score_type=reason.score_type,
                score_contribution=(
                    reason.score_contribution
                ),
                # 원점수 사유를 최종 가중 점수에 배분하는
                # 정책은 아직 정하지 않았으므로 기록하지 않음
                final_score_contribution=None,
            )
        )

    db.flush()
    return assessment