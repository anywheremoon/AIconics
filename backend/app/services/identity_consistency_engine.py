def calculate_identity_score(
    *,
    device_trust_status: str,
    repeated_login_detected: bool,
    account_switch_detected: bool,
    ip_changed: bool = False,
    location_changed: bool = False,
    baseline_status: str = "AVAILABLE",
) -> dict:
    score = 0
    reasons = []
    contributions = {}

    rules = []
    if device_trust_status == "NEW_DEVICE":
        rules.append(("NEW_DEVICE", 20))
    elif device_trust_status == "SHARED_DEVICE":
        rules.append(("SHARED_DEVICE", 25))
    if ip_changed:
        rules.append(("IP_CHANGED", 10))
    if location_changed:
        rules.append(("LOCATION_CHANGED", 15))
    if repeated_login_detected:
        rules.append(("REPEATED_LOGIN", 10))
    if account_switch_detected:
        rules.append(("ACCOUNT_SWITCHING", 20))

    for reason, points in rules:
        score += points
        reasons.append(reason)
        contributions[reason] = points

    return {
        "identity_score": min(score, 100),
        "baseline_status": baseline_status,
        "reason_codes": reasons,
        "contributions": contributions,
    }
