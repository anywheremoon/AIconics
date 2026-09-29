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
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.models.user_session_model import UserSession
from app.services.auth_service import get_current_user
from app.services.transaction_risk_engine import calculate_transaction_risk
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


def test_existing_recipient_and_normal_amount_have_no_risk_reasons():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(db, now)
    add_transfer(db, sender.id, recipient.id, "1000.00", now - timedelta(days=2))

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "1000.00"),
        now=now,
    )

    assert result["transaction_score"] == 0
    assert result["is_new_recipient"] is False
    assert result["is_unusually_large"] is False
    assert result["average_transfer_amount"] == Decimal("1000.0")
    assert result["reasons"] == []
    db.close()


def test_detects_transfer_three_times_larger_than_historical_average():
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

    assert result["transaction_score"] == 20
    assert result["is_unusually_large"] is True
    assert result["reasons"] == ["UNUSUALLY_LARGE_TRANSFER"]
    db.close()


def test_velocity_uses_projected_ten_minute_count_and_hourly_amount():
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

    assert result["transaction_score"] == 45
    assert result["recent_10_minute_count"] == 4
    assert result["projected_10_minute_count"] == 5
    assert result["recent_1_hour_amount"] == Decimal("9600000.00")
    assert result["projected_1_hour_amount"] == Decimal("10100000.00")
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

    other_user = User(username=f"other-{uuid4()}", password_hash="hash")
    db.add(other_user)
    db.flush()
    other_recipient = Account(
        user_id=other_user.id,
        account_number=f"{other_user.id:012d}",
        balance=Decimal("0.00"),
        opened_at=now - timedelta(days=30),
    )
    db.add(other_recipient)
    db.commit()
    add_transfer(
        db,
        sender.id,
        other_recipient.id,
        "100000.00",
        now - timedelta(hours=2),
    )

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


def test_detects_transfer_of_most_balance_shortly_after_incoming_transfer():
    now = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    db = TestingSessionLocal()
    user, sender, recipient, session_id = create_risk_context(db, now)
    add_transfer(
        db,
        sender.id,
        recipient.id,
        "500000.00",
        now - timedelta(days=2),
    )

    funding_user = User(username=f"funding-{uuid4()}", password_hash="hash")
    db.add(funding_user)
    db.flush()
    funding_account = Account(
        user_id=funding_user.id,
        account_number=f"{funding_user.id:012d}",
        balance=Decimal("1000000.00"),
        opened_at=now - timedelta(days=30),
    )
    db.add(funding_account)
    sender.balance = Decimal("1000000.00")
    db.commit()
    add_transfer(
        db,
        funding_account.id,
        sender.id,
        "900000.00",
        now - timedelta(minutes=5),
    )

    result = calculate_transaction_risk(
        db,
        user.id,
        risk_request(session_id, recipient, "800000.00"),
        now=now,
    )

    assert result["transaction_score"] == 25
    assert result["recent_incoming_amount"] == Decimal("900000.00")
    assert result["is_rapid_balance_drain"] is True
    assert result["reasons"] == ["RAPID_BALANCE_DRAIN"]
    db.close()


def test_transaction_risk_api_returns_score_for_authenticated_user(client):
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
    body = response.json()
    assert body["transaction_score"] == 85
    assert body["is_new_recipient"] is True
    assert body["account_age_days"] == 0
    assert body["minutes_after_login"] <= 5
    assert body["recent_10_minute_count"] == 0
    assert body["projected_10_minute_count"] == 1
    assert body["is_new_account_high_amount"] is True
    assert body["is_rapid_balance_drain"] is False


def test_transaction_risk_api_rejects_another_users_session(client):
    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    user, _, recipient, _ = create_risk_context(db, now)
    other_user, _, _, other_session_id = create_risk_context(db, now)
    user_id = user.id
    other_user_id = other_user.id
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

    assert other_user_id != user_id
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Session does not belong to the authenticated user"
    )
