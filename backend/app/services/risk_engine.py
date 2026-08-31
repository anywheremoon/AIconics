from app.services.ml_engine import detect_anomaly


def calculate_risk_score(
    event_data,
    profile_comparison: dict | None = None,
):
    """
    Profile 비교 결과와 One-Class SVM 결과를 합쳐
    최종 Risk Score를 계산한다.
    """

    comparison = profile_comparison or {}

    # Profile Comparison에서 계산한 점수
    score = int(
        comparison.get(
            "profile_deviation_score",
            0,
        )
    )

    # Pydantic 객체 또는 dict 모두 처리
    if hasattr(event_data, "model_dump"):
        event_dict = event_data.model_dump()
    else:
        event_dict = dict(event_data)

    # ==========================
    # ML 이상 탐지
    # ==========================
    ml_result = detect_anomaly(event_dict)

    if ml_result["is_anomaly"]:
        score += 30

    # ==========================
    # 최종 점수
    # ==========================
    final_score = min(score, 100)

    return {
        "risk_score": final_score,
        "risk_level": get_risk_level(final_score),
        "is_anomaly": ml_result["is_anomaly"],
        "ml_prediction": ml_result["prediction"],
        "ml_decision_score": ml_result["decision_score"],
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