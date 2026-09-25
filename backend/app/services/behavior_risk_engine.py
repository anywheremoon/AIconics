def calculate_behavior_score(comparison: dict, ml_result: dict) -> dict:
    score = 0
    reasons = []
    contributions = {}

    rules = (
        ("TYPING_ANOMALY", comparison.get("typing_deviation", 0.0), 15),
        ("HOLD_TIME_ANOMALY", comparison.get("hold_time_deviation", 0.0), 10),
        ("FLIGHT_TIME_ANOMALY", comparison.get("flight_time_deviation", 0.0), 10),
    )
    for reason, deviation, points in rules:
        if deviation >= 0.5:
            score += points
            reasons.append(reason)
            contributions[reason] = points

    if max(
        comparison.get("mouse_deviation", 0.0),
        comparison.get("click_deviation", 0.0),
    ) >= 0.5:
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
