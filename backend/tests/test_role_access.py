import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.repositories import user_repository
from app.services.auth_service import hash_password
from app.models.device_model import Device
from app.models.event_model import Event
from app.models.user_session_model import UserSession
from main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


def create_user(db, username: str, password: str = "password1234", role: str = "USER"):
    user = user_repository.create_user(db, username, hash_password(password))
    if role != "USER":
        user_repository.update_role(db, user, role)
    db.commit()
    db.refresh(user)
    return user


def login(client: TestClient, username: str, password: str = "password1234"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def test_new_user_role_is_user(db):
    user = create_user(db, "user01")

    assert user.role == "USER"


def test_register_then_login_round_trip(client, db):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "new_user",
            "password": "password1234",
            "device_id": "test-device",
            "location": "Seoul",
        },
    )

    assert register_response.status_code == 201
    registered_user = user_repository.find_by_username(db, "new_user")
    assert registered_user is not None
    assert registered_user.role == "USER"

    login_response = login(client, "new_user")

    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "USER"
    assert login_response.json()["access_token"]


def test_login_response_includes_user_role(client, db):
    user = create_user(db, "user01")

    response = login(client, user.username)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": user.id,
        "username": user.username,
        "role": "USER",
    }


def test_get_current_user(client, db):
    user = create_user(db, "user01")
    token = login(client, user.username).json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "role": "USER",
    }


def test_get_current_user_without_token_returns_401(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_user_cannot_list_events(client, db):
    user = create_user(db, "user01")
    token = login(client, user.username).json()["access_token"]

    response = client.get(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_events(client, db):
    admin = create_user(db, "admin", role="ADMIN")
    token = login(client, admin.username).json()["access_token"]

    response = client.get(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []

def test_user_cannot_get_event_detail(client, db):
    user = create_user(db, "detail_user")
    token = login(client, user.username).json()["access_token"]

    response = client.get(
        "/api/events/999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_get_nonexistent_event_returns_404(client, db):
    admin = create_user(db, "detail_admin", role="ADMIN")
    token = login(client, admin.username).json()["access_token"]

    response = client.get(
        "/api/events/999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"

def test_admin_can_get_event_detail(client, db):
    admin = create_user(db, "event_admin", role="ADMIN")
    token = login(client, admin.username).json()["access_token"]

    device = Device(
        device_id="detail-test-device",
    )
    db.add(device)
    db.flush()

    user_session = UserSession(
        session_id="00000000-0000-4000-8000-000000000001",
        user_id=admin.id,
        device_id=device.device_id,
        ip_address="127.0.0.1",
        location="Seoul",
        device_trust_status="TRUSTED_DEVICE",
        repeated_login_detected=False,
        account_switch_detected=False,
        recent_login_count=1,
        recent_device_account_count=1,
    )
    db.add(user_session)
    db.flush()

    event = Event(
        user_id=str(admin.id),
        session_id=user_session.session_id,
        device_id=device.device_id,
        ip_address="127.0.0.1",
        location="Seoul",
        typing_speed=2.0,
        avg_hold_time=100.0,
        avg_flight_time=200.0,
        total_keystrokes=20,
        mouse_move_count=10,
        click_count=2,
        is_new_device=False,
        profile_deviation_score=10.0,
        detect_anomaly=False,
        behavior_score=20.0,
        identity_score=10.0,
        baseline_status="AVAILABLE",
        reasons=[],
        risk_score=30.0,
        risk_level="LOW",
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    response = client.get(
        f"/api/events/{event.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == event.id
    assert body["session_id"] == user_session.session_id
    assert body["device_id"] == "detail-test-device"
    assert body["ip_address"] == "127.0.0.1"
    assert body["behavior_score"] == 20.0
    assert body["identity_score"] == 10.0
    assert body["risk_score"] == 30.0
    assert body["risk_level"] == "LOW"
    assert body["baseline_status"] == "AVAILABLE"
    assert body["detect_anomaly"] is False
    assert body["reasons"] == []