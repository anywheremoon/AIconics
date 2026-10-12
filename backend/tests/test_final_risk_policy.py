import pytest

from app.services.risk_decision_service import assess_final_risk
from app.services.score_combiner import calculate_final_risk


def _reason(code: str, score_type: str, contribution: float) -> dict:
    return {
        "reason_code": code,
        "description": f"{score_type}: {code}",
        "score_type": score_type,
        "score_contribution": contribution,
    }


def test_graph_score_contributes_to_final_risk():
    result = assess_final_risk(
        behavior_score=0,
        identity_score=0,
        transaction_score=0,
        graph_score=100,
        graph_reasons=[_reason("COMMON_BENEFICIARY", "GRAPH", 100)],
    )

    assert result.graph_score == 100
    assert result.weighted_contributions.graph == 20
    assert result.final_risk_score == 20
    assert result.effective_scores["graph"] == 100


def test_four_domain_weights_sum_to_one():
    result = calculate_final_risk(
        behavior_score=65,
        identity_score=80,
        transaction_score=100,
        graph_score=100,
    )

    assert sum(result["applied_weights"].values()) == pytest.approx(1)
    assert result["applied_weights"] == {
        "behavior": 0.24,
        "identity": 0.28,
        "transaction": 0.28,
        "graph": 0.20,
    }
    assert result["final_risk_score"] == 100


def test_three_domain_weights_are_used_when_graph_is_unavailable():
    result = calculate_final_risk(
        behavior_score=65,
        identity_score=80,
        transaction_score=100,
        graph_score=None,
    )

    assert sum(result["applied_weights"].values()) == pytest.approx(1)
    assert result["applied_weights"] == {
        "behavior": 0.30,
        "identity": 0.35,
        "transaction": 0.35,
        "graph": 0.0,
    }
    assert result["final_risk_score"] == 100


def test_shared_device_is_not_scored_in_identity_and_graph():
    result = assess_final_risk(
        behavior_score=0,
        identity_score=25,
        transaction_score=0,
        graph_score=25,
        identity_reasons=[_reason("SHARED_DEVICE", "IDENTITY", 25)],
        graph_reasons=[_reason("SHARED_DEVICE", "GRAPH", 25)],
    )

    assert result.graph_score == 25
    assert result.effective_scores["graph"] == 0
    assert result.duplicate_score_deductions == {"graph": 25}
    assert result.weighted_contributions.graph == 0
    assert result.final_risk_score == pytest.approx(8.75)
    assert [(reason.score_type, reason.reason_code) for reason in result.reasons] == [
        ("IDENTITY", "SHARED_DEVICE")
    ]
