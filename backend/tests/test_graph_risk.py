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


def test_graph_compound_pattern_does_not_double_count_components(monkeypatch):
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

    # The compound pattern supersedes SHARED_DEVICE and COMMON_BENEFICIARY,
    # so those underlying facts are not scored twice.
    assert result["graph_score"] == 50
    assert result["reasons"] == [
        "SHARED_IP_DEVICE",
        "SHARED_DEVICE_COMMON_BENEFICIARY",
    ]
    assert [
        reason["score_contribution"] for reason in result["reason_details"]
    ] == [15, 35]
