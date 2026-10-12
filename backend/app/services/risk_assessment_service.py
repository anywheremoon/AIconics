from sqlalchemy.orm import Session

from app.models.risk_assessment_model import RiskAssessment
from app.models.risk_factor_model import RiskFactor
from app.schemas.final_risk_schema import FinalRiskResult
from app.services.score_combiner import (
    BEHAVIOR_RAW_MAX,
    IDENTITY_RAW_MAX,
)


POLICY_VERSION = "weighted_rules_v3_normalized_graph_deduplicated"


def _final_reason_contributions(
    result: FinalRiskResult,
) -> dict[tuple[str, str], float]:
    """Allocate the actual capped final score across retained reasons."""
    domain_totals: dict[str, float] = {}
    for reason in result.reasons:
        domain_totals[reason.score_type] = (
            domain_totals.get(reason.score_type, 0.0)
            + reason.score_contribution
        )

    weighted = result.weighted_contributions.model_dump()
    weighted_total = sum(weighted.values())
    cap_scale = (
        result.final_risk_score / weighted_total
        if weighted_total > 0
        else 0.0
    )

    contributions = {}
    for reason in result.reasons:
        domain_total = domain_totals[reason.score_type]
        domain_weighted = weighted[reason.score_type.lower()]
        contributions[(reason.score_type, reason.reason_code)] = (
            domain_weighted
            * cap_scale
            * reason.score_contribution
            / domain_total
        )
    return contributions


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

    final_reason_contributions = _final_reason_contributions(result)

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
                **result.applied_weights,
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
            "effective_scores": result.effective_scores,
            "duplicate_score_deductions": (
                result.duplicate_score_deductions
            ),
            "graph_included_in_final_score": (
                result.graph_score is not None
            ),
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
                final_score_contribution=final_reason_contributions[
                    (reason.score_type, reason.reason_code)
                ],
            )
        )

    db.flush()
    return assessment
