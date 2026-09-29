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