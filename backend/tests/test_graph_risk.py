from app.services import graph_risk_engine


def _mock_detectors(
    monkeypatch,
    shared_devices=None,
    shared_ip_devices=None,
    common_beneficiaries=None,
    compound_patterns=None,
):
    monkeypatch.setattr(
        graph_risk_engine,
        "detect_shared_device",
        lambda user_id: shared_devices or [],
    )
    monkeypatch.setattr(
        graph_risk_engine,
        "detect_shared_ip_device",
        lambda user_id: shared_ip_devices or [],
    )
    monkeypatch.setattr(
        graph_risk_engine,
        "detect_common_beneficiary",
        lambda user_id: common_beneficiaries or [],
    )
    monkeypatch.setattr(
        graph_risk_engine,
        "detect_shared_device_common_beneficiary",
        lambda user_id: compound_patterns or [],
    )


def test_graph_risk_no_patterns(monkeypatch):
    _mock_detectors(monkeypatch)

    result = graph_risk_engine.analyze_graph_risk(1)

    assert result["user_id"] == 1
    assert result["graph_score"] == 0
    assert result["reasons"] == []


def test_graph_risk_shared_device(monkeypatch):
    shared_devices = [
        {
            "device_id": "device-001",
            "other_user_count": 1,
        }
    ]

    _mock_detectors(
        monkeypatch,
        shared_devices=shared_devices,
    )

    result = graph_risk_engine.analyze_graph_risk(1)

    assert result["graph_score"] == 25
    assert result["reasons"] == ["SHARED_DEVICE"]
    assert result["shared_devices"] == shared_devices


def test_graph_risk_multiple_patterns(monkeypatch):
    _mock_detectors(
        monkeypatch,
        shared_devices=[{"device_id": "device-001"}],
        shared_ip_devices=[
            {
                "device_id": "device-001",
                "ip_address": "127.0.0.1",
            }
        ],
        common_beneficiaries=[
            {"recipient_account_id": 10}
        ],
    )

    result = graph_risk_engine.analyze_graph_risk(1)

    assert result["graph_score"] == 65
    assert result["reasons"] == [
        "SHARED_DEVICE",
        "SHARED_IP_DEVICE",
        "COMMON_BENEFICIARY",
    ]


def test_graph_risk_score_is_capped_at_100(monkeypatch):
    _mock_detectors(
        monkeypatch,
        shared_devices=[{"device_id": "device-001"}],
        shared_ip_devices=[
            {
                "device_id": "device-001",
                "ip_address": "127.0.0.1",
            }
        ],
        common_beneficiaries=[
            {"recipient_account_id": 10}
        ],
        compound_patterns=[
            {
                "device_id": "device-001",
                "recipient_account_id": 10,
            }
        ],
    )

    result = graph_risk_engine.analyze_graph_risk(1)

    assert result["graph_score"] == 100
    assert result["reasons"] == [
        "SHARED_DEVICE",
        "SHARED_IP_DEVICE",
        "COMMON_BENEFICIARY",
        "SHARED_DEVICE_COMMON_BENEFICIARY",
    ]