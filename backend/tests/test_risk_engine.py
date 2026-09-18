from unittest.mock import patch

from app.services.risk_engine import calculate_risk_score


EVENT_DATA = {
    "typing_speed": 2.0,
    "avg_hold_time": 100.0,
    "avg_flight_time": 200.0,
    "total_keystrokes": 20,
    "mouse_move_count": 10,
    "click_count": 2,
}

PROFILE_ANOMALY = {
    "typing_deviation": 1.0,
    "hold_time_deviation": 1.0,
    "flight_time_deviation": 1.0,
    "mouse_deviation": 1.0,
    "click_deviation": 1.0,
    "ip_changed": True,
    "location_changed": True,
    "profile_deviation_score": 70,
}


def _normal_ml_result(_event):
    return {
        "is_anomaly": False,
        "prediction": 1,
        "decision_score": 0.5,
    }


def _anomalous_ml_result(_event):
    return {
        "is_anomaly": True,
        "prediction": -1,
        "decision_score": -0.5,
    }


@patch("app.services.risk_engine.detect_anomaly", side_effect=_normal_ml_result)
def test_insufficient_profile_does_not_affect_risk(_detect_anomaly):
    result = calculate_risk_score(
        EVENT_DATA,
        PROFILE_ANOMALY,
        baseline_status="INSUFFICIENT_DATA",
    )

    assert result["behavior_score"] == 0
    assert result["identity_score"] == 0
    assert result["risk_score"] == 0
    assert result["profile_deviation_score"] == 0
    assert result["reasons"] == []


@patch("app.services.risk_engine.detect_anomaly", side_effect=_anomalous_ml_result)
def test_insufficient_profile_keeps_ml_and_independent_rules(_detect_anomaly):
    result = calculate_risk_score(
        EVENT_DATA,
        PROFILE_ANOMALY,
        baseline_status="INSUFFICIENT_DATA",
        device_trust_status="NEW_DEVICE",
        repeated_login_detected=True,
        account_switch_detected=True,
    )

    assert result["behavior_score"] == 20
    assert result["identity_score"] == 50
    assert result["risk_score"] == 70
    assert result["profile_deviation_score"] == 0
    assert {reason["reason_code"] for reason in result["reasons"]} == {
        "ML_ANOMALY",
        "NEW_DEVICE",
        "REPEATED_LOGIN",
        "ACCOUNT_SWITCHING",
    }


@patch("app.services.risk_engine.detect_anomaly", side_effect=_normal_ml_result)
def test_available_profile_affects_risk(_detect_anomaly):
    result = calculate_risk_score(
        EVENT_DATA,
        PROFILE_ANOMALY,
        baseline_status="AVAILABLE",
    )

    assert result["behavior_score"] == 45
    assert result["identity_score"] == 25
    assert result["risk_score"] == 70
    assert result["profile_deviation_score"] == 70