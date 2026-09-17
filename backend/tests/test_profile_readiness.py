from types import SimpleNamespace
from unittest.mock import patch

from app.services import user_profile_service
from app.services.risk_engine import calculate_risk_score


EVENT_DATA = {
    "typing_speed": 2.0,
    "avg_hold_time": 100.0,
    "avg_flight_time": 500.0,
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

NORMAL_ML_RESULT = {
    "is_anomaly": False,
    "prediction": 1,
    "decision_score": 0.5,
}


def _baseline_status_for(event_count):
    profile = SimpleNamespace(event_count=event_count)
    with patch.object(user_profile_service, "get_user_baseline", return_value=profile):
        return user_profile_service.get_baseline_status(object(), user_id=1)


def test_profile_is_not_ready_before_ten_events():
    assert _baseline_status_for(9) == user_profile_service.BASELINE_INSUFFICIENT_DATA


def test_profile_is_ready_at_ten_events():
    assert _baseline_status_for(10) == user_profile_service.BASELINE_AVAILABLE


@patch("app.services.risk_engine.detect_anomaly", return_value=NORMAL_ML_RESULT)
def test_baseline_is_applied_only_after_profile_is_ready(_detect_anomaly):
    insufficient_result = calculate_risk_score(
        EVENT_DATA,
        PROFILE_ANOMALY,
        baseline_status=_baseline_status_for(9),
    )
    available_result = calculate_risk_score(
        EVENT_DATA,
        PROFILE_ANOMALY,
        baseline_status=_baseline_status_for(10),
    )

    assert insufficient_result["risk_score"] == 0
    assert insufficient_result["profile_deviation_score"] == 0
    assert available_result["risk_score"] == 70
    assert available_result["profile_deviation_score"] == 70
