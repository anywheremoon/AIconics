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

def analyze_graph_risk(user_id: int) -> dict:
    shared_devices = detect_shared_device(user_id)
    shared_ip_devices = detect_shared_ip_device(user_id)
    common_beneficiaries = detect_common_beneficiary(user_id)
    compound_patterns = detect_shared_device_common_beneficiary(user_id)

    reasons = []

    if shared_devices:
        reasons.append("SHARED_DEVICE")

    if shared_ip_devices:
        reasons.append("SHARED_IP_DEVICE")

    if common_beneficiaries:
        reasons.append("COMMON_BENEFICIARY")

    if compound_patterns:
        reasons.append("SHARED_DEVICE_COMMON_BENEFICIARY")

    graph_score = min(
    sum(GRAPH_RISK_WEIGHTS[reason] for reason in reasons),
    100,
)

    return {
        "user_id": user_id,
        "graph_score": graph_score,
        "reasons": reasons,
        "shared_devices": shared_devices,
        "shared_ip_devices": shared_ip_devices,
        "common_beneficiaries": common_beneficiaries,
        "compound_patterns": compound_patterns,
    }