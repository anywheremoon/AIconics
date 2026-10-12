from app.schemas.final_risk_schema import FinalRiskResult
from app.services.risk_explanation_service import (
    merge_risk_reasons_with_deductions,
)
from app.services.score_combiner import (
    calculate_final_risk,
    validate_score,
)


def decide_risk(final_risk_score) -> dict:
    """최종 점수에 따라 위험 등급과 거래 결정을 반환한다."""

    score = validate_score(
        final_risk_score,
        "final_risk_score",
    )

    if score < 40:
        risk_level = "LOW"
        decision = "APPROVED"

    elif score < 70:
        risk_level = "MEDIUM"
        decision = "REQUIRE_VERIFICATION"

    elif score < 85:
        risk_level = "HIGH"
        decision = "PENDING_REVIEW"

    else:
        risk_level = "CRITICAL"
        decision = "ACCOUNT_REVIEW"

    return {
        "final_risk_score": score,
        "risk_level": risk_level,
        "decision": decision,
        "requires_verification": (
            decision == "REQUIRE_VERIFICATION"
        ),
        "risk_allows_immediate_transfer": (
            decision == "APPROVED"
        ),
    }

DECISION_TO_TRANSACTION_STATUS = {
    "APPROVED": "COMPLETED",
    "REQUIRE_VERIFICATION": "PENDING_VERIFICATION",
    "PENDING_REVIEW": "PENDING_REVIEW",
    "ACCOUNT_REVIEW": "ACCOUNT_REVIEW",
}


def transaction_status_for_decision(decision: str) -> str:
    """위험 평가 결정을 거래 저장 상태로 변환한다."""
    try:
        return DECISION_TO_TRANSACTION_STATUS[decision]
    except (KeyError, TypeError) as error:
        raise ValueError(
            f"지원하지 않는 위험 평가 결정입니다: {decision}"
        ) from error

def assess_final_risk(
    *,
    behavior_score,
    identity_score,
    transaction_score,
    behavior_reasons=None,
    identity_reasons=None,
    transaction_reasons=None,
    graph_score=None,
    graph_reasons=None,
) -> FinalRiskResult:
    """각 영역의 점수와 사유를 최종 위험 평가 결과로 묶는다."""

    checked_graph_score = (
        validate_score(graph_score, "graph_score")
        if graph_score is not None
        else None
    )

    reasons, duplicate_deductions = merge_risk_reasons_with_deductions(
        behavior_reasons or [],
        identity_reasons or [],
        transaction_reasons or [],
        graph_reasons or [],
    )

    raw_scores = {
        "BEHAVIOR": validate_score(behavior_score, "behavior_score"),
        "IDENTITY": validate_score(identity_score, "identity_score"),
        "TRANSACTION": validate_score(transaction_score, "transaction_score"),
        "GRAPH": checked_graph_score,
    }
    effective_scores = {
        score_type: max(
            0.0,
            score - duplicate_deductions.get(score_type, 0.0),
        )
        for score_type, score in raw_scores.items()
        if score is not None
    }

    combined = calculate_final_risk(
        behavior_score=effective_scores["BEHAVIOR"],
        identity_score=effective_scores["IDENTITY"],
        transaction_score=effective_scores["TRANSACTION"],
        graph_score=effective_scores.get("GRAPH"),
    )

    decision = decide_risk(combined["final_risk_score"])

    return FinalRiskResult(
        # Persist original engine outputs.  Effective scores and deductions
        # below make the no-double-count calculation auditable.
        behavior_score=raw_scores["BEHAVIOR"],
        identity_score=raw_scores["IDENTITY"],
        transaction_score=raw_scores["TRANSACTION"],
        graph_score=checked_graph_score,
        normalized_behavior_score=(
            combined["normalized_behavior_score"]
        ),
        normalized_identity_score=(
            combined["normalized_identity_score"]
        ),
        weighted_contributions=(
            combined["weighted_contributions"]
        ),
        applied_weights=combined["applied_weights"],
        effective_scores={
            key.lower(): value for key, value in effective_scores.items()
        },
        duplicate_score_deductions={
            key.lower(): value for key, value in duplicate_deductions.items()
        },
        final_risk_score=decision["final_risk_score"],
        risk_level=decision["risk_level"],
        decision=decision["decision"],
        reasons=reasons,
    )
