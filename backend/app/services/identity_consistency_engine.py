def calculate_identity_score(
    *,
    device_trust_status: str,
    repeated_login_detected: bool,
    account_switch_detected: bool,
    ip_changed: bool = False,
    location_changed: bool = False,
    baseline_status: str = "AVAILABLE",
) -> dict:
    """
    세션/장치/접속 일관성을 기반으로 Identity Score를 계산한다.
    """

    score = 0
    reasons = []
    contributions = {}

    if device_trust_status == "NEW_DEVICE":
        score += 20
        reasons.append("NEW_DEVICE")
        contributions["NEW_DEVICE"] = 20

    elif device_trust_status == "SHARED_DEVICE":
        score += 25
        reasons.append("SHARED_DEVICE")
        contributions["SHARED_DEVICE"] = 25

    if ip_changed:
        score += 10
        reasons.append("IP_CHANGED")
        contributions["IP_CHANGED"] = 10

    if location_changed:
        score += 15
        reasons.append("LOCATION_CHANGED")
        contributions["LOCATION_CHANGED"] = 15

    if repeated_login_detected:
        score += 10
        reasons.append("REPEATED_LOGIN")
        contributions["REPEATED_LOGIN"] = 10

    if account_switch_detected:
        score += 20
        reasons.append("ACCOUNT_SWITCHING")
        contributions["ACCOUNT_SWITCHING"] = 20

    return {
        "identity_score": min(score, 100),
        "baseline_status": baseline_status,
        "reason_codes": reasons,
        "contributions": contributions,
    }