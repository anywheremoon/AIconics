
from app.models.risk_assessment_model import RiskAssessment
from app.services.risk_hash_service import generate_risk_hash


def make_assessment():
    return RiskAssessment(
        transaction_id=101,
        behavior_score=20.0,
        identity_score=30.0,
        transaction_score=40.0,
        graph_score=None,
        final_risk_score=75.0,
        risk_level="HIGH",
        decision="REQUIRE_VERIFICATION",
        policy_version="test_v1",
        calculation_details={
            "weights": {
                "behavior": 0.3,
                "identity": 0.7,
            }
        },
    )


def test_same_data_produces_same_hash():
    assessment = make_assessment()

    assert generate_risk_hash(assessment) == generate_risk_hash(
        assessment
    )


def test_changed_risk_score_produces_different_hash():
    assessment = make_assessment()
    original_hash = generate_risk_hash(assessment)

    assessment.final_risk_score = 85.0

    assert generate_risk_hash(assessment) != original_hash


def test_hash_has_64_hex_characters():
    assessment = make_assessment()
    result = generate_risk_hash(assessment)

    assert len(result) == 64
    assert all(character in "0123456789abcdef" for character in result)


def test_json_key_order_does_not_change_hash():
    assessment = make_assessment()
    original_hash = generate_risk_hash(assessment)

    assessment.calculation_details = {
        "weights": {
            "identity": 0.7,
            "behavior": 0.3,
        }
    }

    assert generate_risk_hash(assessment) == original_hash
