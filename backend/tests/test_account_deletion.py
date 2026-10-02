import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.user_model import User
from app.services.auth_service import get_current_user
from app.models.device_model import Device
from app.models.event_model import Event
from app.models.user_session_model import UserSession
from app.models.transaction_model import Transaction
from main import app


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
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


def create_user(username: str = "delete-user") -> int:
    db = TestingSessionLocal()

    user = User(
        username=username,
        password_hash="test-password-hash",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    user_id = user.id
    db.close()

    return user_id


def authenticate_as(user_id: int):
    def override_get_current_user():
        db = TestingSessionLocal()
        try:
            return db.get(User, user_id)
        finally:
            db.close()

    app.dependency_overrides[get_current_user] = override_get_current_user


def test_delete_current_user(client):
    user_id = create_user()
    authenticate_as(user_id)

    response = client.delete("/api/auth/me")

    assert response.status_code == 204

    db = TestingSessionLocal()
    deleted_user = db.get(User, user_id)
    db.close()

    assert deleted_user is None

def test_delete_user_with_session_and_event(client):
    user_id = create_user("delete-user-with-event")

    db = TestingSessionLocal()

    device = Device(
        device_id="delete-test-device",
    )
    db.add(device)
    db.flush()

    session = UserSession(
        session_id="delete-test-session",
        user_id=user_id,
        device_id=device.device_id,
        ip_address="127.0.0.1",
        location="Seoul",
        device_trust_status="TRUSTED_DEVICE",
        repeated_login_detected=False,
        account_switch_detected=False,
        recent_login_count=1,
        recent_device_account_count=1,
    )
    db.add(session)
    db.flush()

    event = Event(
        user_id=str(user_id),
        session_id=session.session_id,
        device_id=device.device_id,
        ip_address="127.0.0.1",
        location="Seoul",
        typing_speed=0,
        avg_hold_time=0,
        avg_flight_time=0,
        total_keystrokes=0,
        mouse_move_count=0,
        click_count=0,
        is_new_device=False,
        profile_deviation_score=0,
        detect_anomaly=False,
        behavior_score=0,
        identity_score=0,
        baseline_status="AVAILABLE",
        reasons=[],
        risk_score=20,
        risk_level="LOW",
    )
    db.add(event)
    db.commit()

    session_id = session.session_id
    event_id = event.id
    db.close()

    authenticate_as(user_id)

    response = client.delete("/api/auth/me")

    assert response.status_code == 204

    db = TestingSessionLocal()

    assert db.get(User, user_id) is None
    assert db.get(Event, event_id) is None
    assert db.get(UserSession, session_id) is None

    db.close()

def test_delete_user_with_account(client):
    from app.models.account_model import Account

    user_id = create_user("delete-user-with-account")

    db = TestingSessionLocal()

    account = Account(
        user_id=user_id,
        account_number="999999999999",
        balance=100000,
    )
    db.add(account)
    db.commit()

    account_id = account.id
    db.close()

    authenticate_as(user_id)

    response = client.delete("/api/auth/me")

    assert response.status_code == 204

    db = TestingSessionLocal()

    assert db.get(User, user_id) is None
    assert db.get(Account, account_id) is None

    db.close()

def test_delete_user_with_transaction(client):
    from app.models.account_model import Account

    sender_id = create_user("delete-user-with-transaction")
    recipient_id = create_user("transaction-recipient")

    db = TestingSessionLocal()

    sender_account = Account(
        user_id=sender_id,
        account_number="888888888888",
        balance=100000,
    )
    recipient_account = Account(
        user_id=recipient_id,
        account_number="777777777777",
        balance=100000,
    )

    db.add_all([sender_account, recipient_account])
    db.flush()

    transaction = Transaction(
        request_id="00000000-0000-4000-8000-000000009999",
        transaction_type="TRANSFER",
        sender_account_id=sender_account.id,
        recipient_account_id=recipient_account.id,
        amount=1000,
        status="COMPLETED",
    )

    db.add(transaction)
    db.commit()

    transaction_id = transaction.id
    db.close()

    authenticate_as(sender_id)

    response = client.delete("/api/auth/me")

    assert response.status_code == 204

    db = TestingSessionLocal()

    assert db.get(User, sender_id) is None
    assert db.query(Account).filter(Account.user_id == sender_id).first() is None
    assert db.get(Transaction, transaction_id) is None

    db.close()

def test_delete_recipient_user_with_transaction(client):
    from app.models.account_model import Account

    sender_id = create_user("transaction-sender")
    recipient_id = create_user("delete-transaction-recipient")

    db = TestingSessionLocal()

    sender_account = Account(
        user_id=sender_id,
        account_number="666666666666",
        balance=100000,
    )
    recipient_account = Account(
        user_id=recipient_id,
        account_number="555555555555",
        balance=100000,
    )

    db.add_all([sender_account, recipient_account])
    db.flush()

    transaction = Transaction(
        request_id="00000000-0000-4000-8000-000000008888",
        transaction_type="TRANSFER",
        sender_account_id=sender_account.id,
        recipient_account_id=recipient_account.id,
        amount=1000,
        status="COMPLETED",
    )

    db.add(transaction)
    db.commit()

    transaction_id = transaction.id
    db.close()

    authenticate_as(recipient_id)

    response = client.delete("/api/auth/me")

    assert response.status_code == 204

    db = TestingSessionLocal()

    # 탈퇴 사용자와 계좌는 삭제
    assert db.get(User, recipient_id) is None
    assert db.query(Account).filter(
        Account.user_id == recipient_id
    ).first() is None

    # 거래 기록은 유지
    transaction = db.get(Transaction, transaction_id)

    assert transaction is not None

    # 삭제된 수취 계좌 연결만 제거
    assert transaction.recipient_account_id is None

    db.close()
