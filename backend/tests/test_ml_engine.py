from app.ml.preprocessing.feature_extractor import WINDOW_DOWN_COUNT
from app.services.ml_engine import detect_anomaly, extract_ml_features


NORMAL_AGENT_EVENT = {
    "typing_speed": 2.0,
    "avg_hold_time": 100.0,
    "avg_flight_time": 500.0,
    "total_keystrokes": 60,
}


def test_ml_input_uses_training_keystroke_window():
    features = extract_ml_features(NORMAL_AGENT_EVENT)

    assert features == [2.0, 100.0, 500.0, float(WINDOW_DOWN_COUNT)]
    assert NORMAL_AGENT_EVENT["total_keystrokes"] == 60


def test_normal_agent_event_is_not_flagged_as_ml_anomaly():
    result = detect_anomaly(NORMAL_AGENT_EVENT)

    assert result["prediction"] == 1
    assert result["is_anomaly"] is False