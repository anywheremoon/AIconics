from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.account_model import Account
from app.models.device_model import Device
from app.models.event_model import Event
from app.models.risk_assessment_model import RiskAssessment
from app.models.risk_factor_model import RiskFactor
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.models.user_session_model import UserSession
from app.services.auth_service import get_current_user
from app.services.transaction_risk_engine import calculate_transaction_risk
from app.services import account_service
from main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def create_risk_context(
    db,
    now: datetime,
    *,
    account_age: timedelta = timedelta(days=30),
    login_age: timedelta = timedelta(hours=1),
):
    sender_user = User(username=f"sender-{uuid4()}", password_hash="hash")
    recipient_user = User(username=f"recipient-{uuid4()}", password_hash="hash")
    db.add_all([sender_user, recipient_user])
    db.flush()

    sender = Account(
        user_id=sender_user.id,
        account_number=f"{sender_user.id:012d}",
        balance=Decimal("50000000.00"),
        opened_at=now - account_age,
    )
    recipient = Account(
        user_id=recipient_user.id,
        account_number=f"{recipient_user.id:012d}",
        balance=Decimal("100000.00"),
        opened_at=now - timedelta(days=30),
    )
    db.add_all([sender, recipient])
    db.flush()

    device_id = f"device-{uuid4()}"
    session_id = str(uuid4())
    db.add(Device(device_id=device_id))
    db.flush()
    db.add(
        UserSession(
            session_id=session_id,
            user_id=sender_user.id,
            device_id=device_id,
            login_at=now - login_age,
            device_trust_status="TRUSTED_DEVICE",
            repeated_login_detected=False,
            account_switch_detected=False,
            recent_login_count=1,
            recent_device_account_count=1,
        )
    )
    db.commit()
    return sender_user, sender, recipient, session_id


def add_transfer(
    db,
    sender_account_id: int,
    recipient_account_id: int,
    amount: str,
    created_at: datetime,
):
    db.add(
        Transaction(
            request_id=str(uuid4()),
            transaction_type="TRANSFER",
            sender_account_id=sender_account_id,
            recipient_account_id=recipient_account_id,
            amount=Decimal(amount),
            status="COMPLETED",
            created_at=created_at,
        )
    )
    db.commit()


def add_behavior_event(
    db,
    user_id: int,
    session_id: str,
    *,
    behavior_score: float = 0,
    identity_score: float = 0,
):
    session = db.get(UserSession, session_id)
    reasons = []
    if identity_score:
        reasons.append(
            {
                "reason_code": "NEW_DEVICE",
                "description": "A new device was detected.",
                "score_type": "IDENTITY",
                "score_contribution": identity_score,
            }
        )
    db.add(
        Event(
            user_id=str(user_id),
            session_id=session_id,
            device_id=session.device_id,
            ip_address="127.0.0.1",
            location="Seoul",
            typing_speed=0,
            avg_hold_time=0,
            avg_flight_time=0,
            total_keystrokes=0,
            mouse_move_count=0,
            click_count=0,
            is_new_device=bool(identity_score),
            profile_deviation_score=0,
            detect_anomaly=False,
            behavior_score=behavior_score,
            identity_score=identity_score,
            baseline_status="AVAILABLE",
            reasons=reasons,
            risk_score=behavior_score + identity_score,
            risk_level="LOW",
        )
    )
    db.commit()


def risk_request(session_id: str, recipient: Account, amount: str):
    return SimpleNamespace(
        session_id=UUID(session_id),
        recipient_account_number=recipient.account_number,
        amount=Decimal(amount),
    )


def test_scores_new_account_recipient_recent_login_and_high_amount():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, _, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=12),
        login_age=timedelta(minutes=3),
    )

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "5000000.00"),
        now=now,
    )

    assert result["transaction_score"] == 85
    assert result["is_new_recipient"] is True
    assert result["account_age_days"] == 0
    assert result["minutes_after_login"] == 3
    assert result["is_high_amount"] is True
    assert result["is_new_account_high_amount"] is True
    assert result["reasons"] == [
        "NEW_ACCOUNT",
        "NEW_RECIPIENT",
        "TRANSFER_SHORTLY_AFTER_LOGIN",
        "HIGH_AMOUNT_TRANSFER",
        "NEW_ACCOUNT_HIGH_AMOUNT",
    ]
    db.close()


def test_account_older_than_exactly_one_day_is_not_new():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, _, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=25),
        login_age=timedelta(hours=1),
    )

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "1000.00"),
        now=now,
    )

    assert result["account_age_days"] == 1
    assert "NEW_ACCOUNT" not in result["reasons"]
    assert result["is_new_account_high_amount"] is False
    db.close()


def test_existing_recipient_and_historical_average_detection():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(db, now)
    add_transfer(db, sender.id, recipient.id, "100000.00", now - timedelta(days=2))

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "300000.00"),
        now=now,
    )

    assert result["is_new_recipient"] is False
    assert result["average_transfer_amount"] == Decimal("100000.0")
    assert result["is_unusually_large"] is True
    assert result["transaction_score"] == 20
    assert result["reasons"] == ["UNUSUALLY_LARGE_TRANSFER"]
    db.close()


def test_velocity_counts_ten_minutes_and_sums_one_hour():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(db, now)
    for minutes_ago in (1, 2, 3, 4):
        add_transfer(
            db,
            sender.id,
            recipient.id,
            "2400000.00",
            now - timedelta(minutes=minutes_ago),
        )

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "500000.00"),
        now=now,
    )

    assert result["recent_10_minute_count"] == 4
    assert result["projected_10_minute_count"] == 5
    assert result["recent_1_hour_amount"] == Decimal("9600000.00")
    assert result["projected_1_hour_amount"] == Decimal("10100000.00")
    assert result["transaction_score"] == 45
    assert result["reasons"] == [
        "VELOCITY_HIGH_FREQUENCY",
        "VELOCITY_HIGH_AMOUNT",
    ]
    db.close()


def test_transaction_score_is_capped_at_one_hundred():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=1),
        login_age=timedelta(minutes=1),
    )
    add_transfer(db, sender.id, recipient.id, "100000.00", now - timedelta(days=2))

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "11000000.00"),
        now=now,
    )

    assert result["transaction_score"] == 100
    assert "UNUSUALLY_LARGE_TRANSFER" in result["reasons"]
    assert "VELOCITY_HIGH_AMOUNT" in result["reasons"]
    db.close()


def test_transaction_risk_api_returns_authenticated_users_score(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, _, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=12),
        login_age=timedelta(minutes=3),
    )
    user_id = user.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)

    response = client.post(
        "/api/risks/transaction",
        json={
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "5000000.00",
        },
    )

    assert response.status_code == 200
    assert response.json()["transaction_score"] == 85
    assert response.json()["recent_10_minute_count"] == 0


def test_transaction_risk_api_rejects_another_users_session(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, _, recipient, _ = create_risk_context(db, now)
    _, _, _, other_session_id = create_risk_context(db, now)
    user_id = user.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)

    response = client.post(
        "/api/risks/transaction",
        json={
            "session_id": other_session_id,
            "recipient_account_number": recipient_number,
            "amount": "1000.00",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Session does not belong to the authenticated user"
    )


def test_transfer_executes_with_server_calculated_low_risk(client, monkeypatch):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(db, now)
    add_transfer(db, sender.id, recipient.id, "1000.00", now - timedelta(days=2))
    add_behavior_event(db, user.id, session_id)
    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    monkeypatch.setattr(
        "app.services.graph_risk_engine.analyze_graph_risk",
        lambda _user_id: {
            "graph_score": 25,
            "reason_details": [
                {
                    "reason_code": "COMMON_BENEFICIARY",
                    "description": "A common beneficiary was detected.",
                    "score_type": "GRAPH",
                    "score_contribution": 25,
                }
            ],
        },
    )
    synced_transactions = []
    monkeypatch.setattr(
        "app.services.assessed_transfer_service.sync_transfer",
        lambda transaction, _sender, _recipient: synced_transactions.append(
            transaction.id
        ) or True,
    )

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "00000000-0000-4000-8000-000000000301",
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "1000.00",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    db = TestingSessionLocal()
    transaction = db.query(Transaction).filter(
        Transaction.request_id == "00000000-0000-4000-8000-000000000301"
    ).one()
    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.transaction_id == transaction.id
    ).one()
    assert assessment.transaction_score == 0
    assert assessment.graph_score == 25
    assert assessment.calculation_details["graph_included_in_final_score"] is True
    assert assessment.calculation_details["weighted_contributions"]["graph"] == 5
    assert assessment.decision == "APPROVED"
    graph_factor = db.query(RiskFactor).filter(
        RiskFactor.risk_assessment_id == assessment.id,
        RiskFactor.score_type == "GRAPH",
    ).one()
    assert graph_factor.reason_code == "COMMON_BENEFICIARY"
    assert graph_factor.final_score_contribution == 5
    assert synced_transactions == [transaction.id]
    assert db.get(Account, sender_id).balance == Decimal("49999000.00")
    assert db.get(Account, recipient_id).balance == Decimal("101000.00")
    db.close()


def test_transfer_persists_risk_and_does_not_move_money_when_verification_required(
    client,
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=12),
        login_age=timedelta(minutes=3),
    )
    add_behavior_event(
        db,
        user.id,
        session_id,
        behavior_score=20,
        identity_score=30,
    )
    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    monkeypatch.setattr(
        "app.services.graph_risk_engine.analyze_graph_risk",
        lambda _user_id: {"graph_score": 0, "reason_details": []},
    )

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "00000000-0000-4000-8000-000000000302",
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "5000000.00",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_VERIFICATION"
    db = TestingSessionLocal()
    transaction = db.query(Transaction).filter(
        Transaction.request_id == "00000000-0000-4000-8000-000000000302"
    ).one()
    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.transaction_id == transaction.id
    ).one()
    factors = db.query(RiskFactor).filter(
        RiskFactor.risk_assessment_id == assessment.id
    ).all()
    assert assessment.transaction_score == 85
    assert assessment.decision == "REQUIRE_VERIFICATION"
    assert {factor.reason_code for factor in factors} >= {
        "NEW_ACCOUNT",
        "NEW_RECIPIENT",
        "TRANSFER_SHORTLY_AFTER_LOGIN",
        "HIGH_AMOUNT_TRANSFER",
    }
    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")
    db.close()


def test_transfer_does_not_move_money_when_final_risk_is_high(client, monkeypatch):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(
        db,
        now,
        account_age=timedelta(hours=12),
        login_age=timedelta(minutes=3),
    )
    add_behavior_event(
        db,
        user.id,
        session_id,
        behavior_score=65,
        identity_score=80,
    )
    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    monkeypatch.setattr(
        "app.services.graph_risk_engine.analyze_graph_risk",
        lambda _user_id: {"graph_score": 0, "reason_details": []},
    )

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "00000000-0000-4000-8000-000000000304",
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "5000000.00",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_REVIEW"
    db = TestingSessionLocal()
    transaction = db.query(Transaction).filter(
        Transaction.request_id == "00000000-0000-4000-8000-000000000304"
    ).one()
    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.transaction_id == transaction.id
    ).one()
    assert assessment.risk_level == "HIGH"
    assert assessment.decision == "PENDING_REVIEW"
    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")
    db.close()


def test_transfer_rejects_historical_session_behavior_event(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, old_session_id = create_risk_context(db, now)
    add_behavior_event(db, user.id, old_session_id)

    device_id = f"device-{uuid4()}"
    current_session_id = str(uuid4())
    db.add(Device(device_id=device_id))
    db.flush()
    db.add(
        UserSession(
            session_id=current_session_id,
            user_id=user.id,
            device_id=device_id,
            login_at=now,
            device_trust_status="TRUSTED_DEVICE",
            repeated_login_detected=False,
            account_switch_detected=False,
            recent_login_count=1,
            recent_device_account_count=1,
        )
    )
    db.commit()
    add_behavior_event(db, user.id, current_session_id)

    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number
    db.close()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "00000000-0000-4000-8000-000000000303",
            "session_id": old_session_id,
            "recipient_account_number": recipient_number,
            "amount": "1000.00",
        },
    )

    assert response.status_code == 409
    db = TestingSessionLocal()
    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")
    assert db.query(Transaction).filter(
        Transaction.request_id == "00000000-0000-4000-8000-000000000303"
    ).count() == 0
    db.close()

def test_transfer_rejects_when_behavior_event_is_missing(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()

    user, sender, recipient, session_id = create_risk_context(db, now)

    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number

    db.close()

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )

    request_id = "00000000-0000-4000-8000-000000000305"

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": request_id,
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "1000.00",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "No behavior event is available for transaction risk assessment"
    )

    db = TestingSessionLocal()

    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")

    assert (
        db.query(Transaction)
        .filter(Transaction.request_id == request_id)
        .count()
        == 0
    )

    db.close()

def test_transfer_rejects_inactive_sender_account(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()

    user, sender, recipient, session_id = create_risk_context(db, now)
    add_behavior_event(db, user.id, session_id)

    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number

    sender.status = "INACTIVE"
    db.commit()
    db.close()

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )

    request_id = "00000000-0000-4000-8000-000000000306"

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": request_id,
            "session_id": session_id,
            "recipient_account_number": recipient_number,
            "amount": "1000.00",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is not active"

    db = TestingSessionLocal()

    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")

    assert (
        db.query(Transaction)
        .filter(Transaction.request_id == request_id)
        .count()
        == 0
    )

    db.close()

def test_transfer_rolls_back_when_risk_assessment_save_fails(
    client,
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()

    user, sender, recipient, session_id = create_risk_context(db, now)
    add_behavior_event(db, user.id, session_id)

    user_id = user.id
    sender_id = sender.id
    recipient_id = recipient.id
    recipient_number = recipient.account_number

    db.close()

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )

    def fail_risk_assessment(*args, **kwargs):
        raise RuntimeError("forced risk assessment failure")

    monkeypatch.setattr(
        account_service,
        "create_risk_assessment",
        fail_risk_assessment,
    )

    request_id = "00000000-0000-4000-8000-000000000307"

    with pytest.raises(
        RuntimeError,
        match="forced risk assessment failure",
    ):
        client.post(
            "/api/transactions/transfer",
            json={
                "request_id": request_id,
                "session_id": session_id,
                "recipient_account_number": recipient_number,
                "amount": "1000.00",
            },
        )

    db = TestingSessionLocal()

    assert (
        db.query(Transaction)
        .filter(Transaction.request_id == request_id)
        .count()
        == 0
    )
    assert db.get(Account, sender_id).balance == Decimal("50000000.00")
    assert db.get(Account, recipient_id).balance == Decimal("100000.00")

    db.close()