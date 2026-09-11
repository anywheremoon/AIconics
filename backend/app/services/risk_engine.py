from app.services.behavior_risk_engine import calculate_behavior_score
from app.services.identity_consistency_engine import calculate_identity_score
from app.services.ml_engine import detect_anomaly
from app.services.risk_explanation_service import build_reasons


def calculate_risk_score(
    event_data,
    profile_comparison: dict | None = None,
    *,
    device_trust_status: str = "TRUSTED_DEVICE",
    repeated_login_detected: bool = False,
    account_switch_detected: bool = False,
    baseline_status: str = "AVAILABLE",
):
    """
    Behavior Score와 Identity Score를 계산하고
    판단 근거를 포함한 최종 위험 분석 결과를 반환한다.
    """

    comparison = profile_comparison or {}

    if hasattr(event_data, "model_dump"):
        event_dict = event_data.model_dump()
    else:
        event_dict = dict(event_data)

    # ==========================
    # 1. ML 이상 탐지
    # ==========================
    ml_result = detect_anomaly(event_dict)

    # ==========================
    # 2. Behavior Score
    # ==========================
    behavior_result = calculate_behavior_score(
        comparison,
        ml_result,
    )

    # ==========================
    # 3. Identity Score
    # ==========================
    identity_result = calculate_identity_score(
        device_trust_status=device_trust_status,
        repeated_login_detected=repeated_login_detected,
        account_switch_detected=account_switch_detected,
        ip_changed=comparison.get("ip_changed", False),
        location_changed=comparison.get(
            "location_changed",
            False,
        ),
        baseline_status=baseline_status,
    )

    behavior_score = behavior_result["behavior_score"]
    identity_score = identity_result["identity_score"]

    # ==========================
    # 4. 최종 Risk Score
    # ==========================
    final_score = min(
        behavior_score + identity_score,
        100,
    )

    # ==========================
    # 5. reason_code / 설명
    # ==========================
    contributions = {}

    contributions.update(
        behavior_result.get(
            "contributions",
            {},
        )
    )

    contributions.update(
        identity_result.get(
            "contributions",
            {},
        )
    )

    reasons = build_reasons(
        behavior_result.get(
            "reason_codes",
            [],
        ),
        identity_result.get(
            "reason_codes",
            [],
        ),
        contributions,
    )

    return {
        "risk_score": final_score,
        "risk_level": get_risk_level(final_score),

        "behavior_score": behavior_score,
        "identity_score": identity_score,
        "baseline_status": identity_result[
            "baseline_status"
        ],

        "reasons": reasons,

        "is_anomaly": ml_result["is_anomaly"],
        "ml_prediction": ml_result["prediction"],
        "ml_decision_score": ml_result[
            "decision_score"
        ],

        "profile_deviation_score": comparison.get(
            "profile_deviation_score",
            0,
        ),
    }


def get_risk_level(score):
    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"