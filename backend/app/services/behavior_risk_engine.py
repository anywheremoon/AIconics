def calculate_behavior_score(
    comparison: dict,
    ml_result: dict,
) -> dict:
    """
    사용자 행동 패턴 기반 Behavior Risk Score 계산.
    """

    score = 0
    reasons = []
    contributions = {}

    typing_deviation = comparison.get("typing_deviation", 0.0)
    hold_time_deviation = comparison.get("hold_time_deviation", 0.0)
    flight_time_deviation = comparison.get("flight_time_deviation", 0.0)
    mouse_deviation = comparison.get("mouse_deviation", 0.0)
    click_deviation = comparison.get("click_deviation", 0.0)

    if typing_deviation >= 0.5:
        score += 15
        reasons.append("TYPING_ANOMALY")
        contributions["TYPING_ANOMALY"] = 15

    if hold_time_deviation >= 0.5:
        score += 10
        reasons.append("HOLD_TIME_ANOMALY")
        contributions["HOLD_TIME_ANOMALY"] = 10

    if flight_time_deviation >= 0.5:
        score += 10
        reasons.append("FLIGHT_TIME_ANOMALY")
        contributions["FLIGHT_TIME_ANOMALY"] = 10

    if max(mouse_deviation, click_deviation) >= 0.5:
        score += 10
        reasons.append("MOUSE_CLICK_ANOMALY")
        contributions["MOUSE_CLICK_ANOMALY"] = 10

    if ml_result.get("is_anomaly", False):
        score += 20
        reasons.append("ML_ANOMALY")
        contributions["ML_ANOMALY"] = 20

    return {
        "behavior_score": min(score, 100),
        "reason_codes": reasons,
        "contributions": contributions,
    }