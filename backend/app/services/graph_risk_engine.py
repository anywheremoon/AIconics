from app.graph.graph_repository import (
    detect_common_beneficiary,
    detect_shared_device,
    detect_shared_device_common_beneficiary,
    detect_shared_ip_device,
)

GRAPH_RISK_WEIGHTS = {
    "SHARED_DEVICE": 25,
    "SHARED_IP_DEVICE": 15,
    "COMMON_BENEFICIARY": 25,
    "SHARED_DEVICE_COMMON_BENEFICIARY": 35,
}

GRAPH_REASON_DESCRIPTIONS = {
    "SHARED_DEVICE": "The user shares a device with another account.",
    "SHARED_IP_DEVICE": "A device and IP address are shared across accounts.",
    "COMMON_BENEFICIARY": "Multiple related accounts transfer to a common beneficiary.",
    "SHARED_DEVICE_COMMON_BENEFICIARY": (
        "Accounts sharing a device also transfer to a common beneficiary."
    ),
}


def _applied_reason_codes(
    *,
    shared_devices: list[dict],
    shared_ip_devices: list[dict],
    common_beneficiaries: list[dict],
    compound_patterns: list[dict],
) -> list[str]:
    """Return mutually exclusive graph factors used by the score.

    The compound pattern already proves both SHARED_DEVICE and
    COMMON_BENEFICIARY. Counting all three would charge the same graph facts
    twice, so the compound factor supersedes those two component factors.
    SHARED_IP_DEVICE remains independent.
    """
    reasons = []

    if shared_ip_devices:
        reasons.append("SHARED_IP_DEVICE")

    if compound_patterns:
        reasons.append("SHARED_DEVICE_COMMON_BENEFICIARY")
        return reasons

    if shared_devices:
        reasons.insert(0, "SHARED_DEVICE")

    if common_beneficiaries:
        reasons.append("COMMON_BENEFICIARY")

    return reasons

def analyze_graph_risk(user_id: int) -> dict:
    shared_devices = detect_shared_device(user_id)
    shared_ip_devices = detect_shared_ip_device(user_id)
    common_beneficiaries = detect_common_beneficiary(user_id)
    compound_patterns = detect_shared_device_common_beneficiary(user_id)

    reasons = _applied_reason_codes(
        shared_devices=shared_devices,
        shared_ip_devices=shared_ip_devices,
        common_beneficiaries=common_beneficiaries,
        compound_patterns=compound_patterns,
    )

    graph_score = min(
        sum(GRAPH_RISK_WEIGHTS[reason] for reason in reasons),
        100,
    )

    reason_details = [
        {
            "reason_code": reason,
            "description": GRAPH_REASON_DESCRIPTIONS[reason],
            "score_type": "GRAPH",
            "score_contribution": GRAPH_RISK_WEIGHTS[reason],
        }
        for reason in reasons
    ]

    return {
        "user_id": user_id,
        "graph_score": graph_score,
        "reasons": reasons,
        "reason_details": reason_details,
        "shared_devices": shared_devices,
        "shared_ip_devices": shared_ip_devices,
        "common_beneficiaries": common_beneficiaries,
        "compound_patterns": compound_patterns,
    }
