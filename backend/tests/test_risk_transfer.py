from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import get_db
from app.routes.risk_transfer import get_risk_transfer_service, router
from app.schemas.risk_transfer_schema import RiskTransferRequest
from app.services.auth_service import get_current_user
from app.services.risk_transfer_service import (
    BlockchainTransferRiskPolicy,
    RiskTransferService,
    latest_aiconics_risk_score,
    normalize_risk_score,
)
from app.services import risk_transfer_service as risk_transfer_module
from app.services.transfer_signature_service import TransferSignatureService


PRIVATE_KEY = "0x" + "11" * 32
SENDER = "0x" + "22" * 20
RECIPIENT = "0x" + "33" * 20
CONTRACT = "0x" + "44" * 20
NOW = 1_780_000_000


def request_data(**changes) -> RiskTransferRequest:
    values = {
        "sender": SENDER,
        "recipient": RECIPIENT,
        "amount": "1000000000000000000",
        "chainId": 31337,
        "verifyingContract": CONTRACT,
    }
    values.update(changes)
    return RiskTransferRequest.model_validate(values)


def make_service(score):
    generated = iter([bytes.fromhex("55" * 32), bytes.fromhex("66" * 32)])
    return RiskTransferService(
        TransferSignatureService(PRIVATE_KEY),
        risk_score_provider=lambda db, user_id, request: score,
        clock=lambda: NOW,
        token_bytes=lambda size: next(generated),
    )


@pytest.mark.parametrize(
    ("score", "expected_name", "expected_code"),
    [
        (0, "LOW", 0),
        (39, "LOW", 0),
        (40, "MEDIUM", 1),
        (69, "MEDIUM", 1),
        (70, "HIGH", 2),
        (84, "HIGH", 2),
        (85, "CRITICAL", 3),
        (100, "CRITICAL", 3),
    ],
)
def test_risk_level_contract_is_stable(score, expected_name, expected_code):
    result = make_service(score).assess_and_sign(
        None,
        user_id=7,
        request=request_data(),
    )

    assert result.risk_score == score
    assert result.risk_level == expected_name
    assert result.risk_level_code == expected_code
    assert result.typed_data.message.risk_level == expected_code
    assert result.typed_data.message.risk_score == score


def test_generates_independent_bytes32_ids_and_default_deadline():
    result = make_service(25).assess_and_sign(
        None,
        user_id=7,
        request=request_data(),
    )

    assert result.request_id == "0x" + "55" * 32
    assert result.nonce == "0x" + "66" * 32
    assert result.request_id != result.nonce
    assert result.deadline == NOW + 300
    assert result.typed_data.message.amount == "1000000000000000000"


@pytest.mark.parametrize("deadline", [NOW, NOW - 1, NOW + 3601])
def test_rejects_expired_or_excessive_deadline(deadline):
    with pytest.raises(HTTPException) as error:
        make_service(25).assess_and_sign(
            None,
            user_id=7,
            request=request_data(deadline=deadline),
        )

    assert error.value.status_code == 422


@pytest.mark.parametrize("value", ["0", "-1", "1.0", "01", "1e18", 100])
def test_amount_requires_positive_canonical_integer_string(value):
    with pytest.raises(ValidationError):
        request_data(amount=value)


def test_rejects_same_sender_and_recipient():
    with pytest.raises(ValidationError):
        request_data(recipient=SENDER.upper().replace("0X", "0x"))


@pytest.mark.parametrize("field", ["sender", "recipient", "verifyingContract"])
def test_rejects_zero_addresses(field):
    with pytest.raises(ValidationError):
        request_data(**{field: "0x" + "0" * 40})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0.4, 0), (0.5, 1), (39.5, 40), (99.5, 100)],
)
def test_normalizes_fractional_engine_score_for_uint8(raw, expected):
    assert normalize_risk_score(raw) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("999", 10), ("1000", 40), ("10000", 70), ("100000", 85)],
)
def test_current_transfer_amount_changes_risk_score(amount, expected):
    policy = BlockchainTransferRiskPolicy(token_decimals=0)
    assert policy.apply(10, request_data(amount=amount)) == expected


def test_chain_contract_and_recipient_signals_change_risk_score():
    blocked = "0x" + "77" * 20
    policy = BlockchainTransferRiskPolicy(
        token_decimals=0,
        trusted_chain_ids=frozenset({1}),
        allowed_contracts=frozenset({"0x" + "88" * 20}),
        blocked_recipients=frozenset({blocked}),
    )

    assert policy.apply(10, request_data(amount="1")) == 70
    assert policy.apply(10, request_data(amount="1", recipient=blocked)) == 100


def test_existing_aiconics_engine_is_recalculated_for_current_transfer(
    monkeypatch,
):
    event = SimpleNamespace(
        session_id="session-1",
        typing_speed=2.0,
        avg_hold_time=100.0,
        avg_flight_time=120.0,
        total_keystrokes=20,
        mouse_move_count=30,
        click_count=4,
        profile_deviation_score=0.1,
        is_new_device=False,
        baseline_status="AVAILABLE",
        risk_score=12,
    )
    session = SimpleNamespace(
        device_trust_status="TRUSTED_DEVICE",
        repeated_login_detected=False,
        account_switch_detected=False,
    )

    class Query:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def first(self):
            return event

    class Database:
        def query(self, model):
            return Query()

        def get(self, model, key):
            assert key == "session-1"
            return session

    calls = []

    def fake_engine(event_data, profile_comparison, **context):
        calls.append((event_data, profile_comparison, context))
        return {"risk_score": 20}

    monkeypatch.setattr(risk_transfer_module, "calculate_risk_score", fake_engine)
    monkeypatch.setenv("AICONICS_TOKEN_DECIMALS", "0")
    monkeypatch.setenv("AICONICS_TRUSTED_CHAIN_IDS", "31337")
    monkeypatch.delenv("AICONICS_ALLOWED_TRANSFER_CONTRACTS", raising=False)
    monkeypatch.delenv("AICONICS_BLOCKED_RECIPIENTS", raising=False)

    score = latest_aiconics_risk_score(
        Database(),
        7,
        request_data(amount="1000"),
    )

    assert score == 40
    assert len(calls) == 1
    assert calls[0][0]["typing_speed"] == 2.0
    assert calls[0][2]["device_trust_status"] == "TRUSTED_DEVICE"


def test_api_returns_frontend_ready_camel_case_contract():
    app = FastAPI()
    app.include_router(router)
    service = make_service(25)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_risk_transfer_service] = lambda: service

    response = TestClient(app).post(
        "/api/risk-transfers/sign",
        json=request_data().model_dump(by_alias=True),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["riskScore"] == 25
    assert body["riskLevel"] == "LOW"
    assert body["riskLevelCode"] == 0
    assert body["typedData"]["primaryType"] == "RiskTransfer"
    assert body["typedData"]["domain"]["chainId"] == 31337
    assert body["typedData"]["message"]["requestId"] == body["requestId"]
    assert body["signature"].startswith("0x")
