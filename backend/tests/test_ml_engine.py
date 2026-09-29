from app.services.ml_engine import detect_anomaly, extract_ml_features


NORMAL_AGENT_EVENT = {
    "typing_speed": 1.73,
    "avg_hold_time": 83.44,
    "avg_flight_time": 503.0,
    "total_keystrokes": 10,
}


def test_ml_input_uses_training_keystroke_window():
    features = extract_ml_features(NORMAL_AGENT_EVENT)

    assert features == [1.73, 83.44, 503.0, 10.0]
    assert NORMAL_AGENT_EVENT["total_keystrokes"] == 10


def test_normal_agent_event_is_not_flagged_as_ml_anomaly():
    result = detect_anomaly(NORMAL_AGENT_EVENT)

    assert result["prediction"] == 1
    assert result["is_anomaly"] is False