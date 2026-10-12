from datetime import datetime, timedelta, timezone

import pytest
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.user_session_model import UserSession
from app.repositories import device_repository, user_repository
from app.services import auth_service
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
def reset_database(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(auth_service, "sync_login", lambda *args: None)
    monkeypatch.setattr(auth_service, "PASSWORD_ITERATIONS", 1_000)
    monkeypatch.setenv("EXPOSE_VERIFICATION_CODE", "true")
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db, username: str):
    user = user_repository.create_user(
        db, username, auth_service.hash_password("password1234")
    )
    db.commit()
    db.refresh(user)
    return user


def login(client, username: str, device_id: str):
    return client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "password1234",
            "device_id": device_id,
        },
    )


def test_login_requires_device_id(client, db):
    user = create_user(db, "missing-device-user")

    response = client.post(
        "/api/auth/login",
        json={
            "username": user.username,
            "password": "password1234",
        },
    )

    assert response.status_code == 422


def test_new_device_requires_verification_and_completes_same_session(
    client, db
):
    user = create_user(db, "verification-user")

    response = login(client, user.username, "new-device")
    assert response.status_code == 200
    login_body = response.json()
    assert login_body["login_status"] == "REQUIRE_VERIFICATION"
    assert login_body["requires_verification"] is True
    assert login_body["reason_codes"] == ["NEW_DEVICE"]
    assert login_body["access_token"] is None
    assert login_body["verification_token"]

    limited_headers = {
        "Authorization": f"Bearer {login_body['verification_token']}"
    }
    protected = client.get("/api/auth/me", headers=limited_headers)
    assert protected.status_code == 401

    issued = client.post(
        "/api/auth/verification/request",
        json={"session_id": login_body["session_id"]},
        headers=limited_headers,
    )
    assert issued.status_code == 200
    code = issued.json()["verification_code"]
    assert code and len(code) == 6

    confirmed = client.post(
        "/api/auth/verification/confirm",
        json={"session_id": login_body["session_id"], "code": code},
        headers=limited_headers,
    )
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()
    assert confirmed_body["login_status"] == "AUTHENTICATED"
    assert confirmed_body["session_id"] == login_body["session_id"]
    assert confirmed_body["access_token"]

    protected = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {confirmed_body['access_token']}"
        },
    )
    assert protected.status_code == 200


def test_trusted_device_authenticates_immediately(client, db):
    user = create_user(db, "trusted-user")
    device_repository.touch_device_and_link(db, "trusted-device", user.id)
    db.commit()

    response = login(client, user.username, "trusted-device")
    assert response.status_code == 200
    body = response.json()
    assert body["login_status"] == "AUTHENTICATED"
    assert body["requires_verification"] is False
    assert body["reason_codes"] == []
    assert body["access_token"]
    assert body["verification_token"] is None


def test_too_many_invalid_codes_moves_session_to_pending(client, db):
    user = create_user(db, "attempt-user")
    login_body = login(client, user.username, "attempt-device").json()
    headers = {
        "Authorization": f"Bearer {login_body['verification_token']}"
    }
    issued = client.post(
        "/api/auth/verification/request",
        json={"session_id": login_body["session_id"]},
        headers=headers,
    )
    correct_code = issued.json()["verification_code"]
    wrong_code = "000000" if correct_code != "000000" else "000001"

    for _ in range(5):
        response = client.post(
            "/api/auth/verification/confirm",
            json={
                "session_id": login_body["session_id"],
                "code": wrong_code,
            },
            headers=headers,
        )
        assert response.status_code == 400

    session = db.get(UserSession, login_body["session_id"])
    db.refresh(session)
    assert session.auth_status == "PENDING"
    assert "TOO_MANY_VERIFICATION_ATTEMPTS" in session.auth_reason_codes

    response = client.post(
        "/api/auth/verification/confirm",
        json={
            "session_id": login_body["session_id"],
            "code": correct_code,
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_shared_device_login_is_pending(client, db):
    owner = create_user(db, "device-owner")
    user = create_user(db, "pending-user")
    device_repository.touch_device_and_link(db, "shared-device", owner.id)
    db.commit()

    response = login(client, user.username, "shared-device")
    assert response.status_code == 200
    body = response.json()
    assert body["login_status"] == "PENDING"
    assert body["requires_verification"] is False
    assert "SHARED_DEVICE" in body["reason_codes"]
    assert body["access_token"] is None
    assert body["verification_token"]

    verification_request = client.post(
        "/api/auth/verification/request",
        json={"session_id": body["session_id"]},
        headers={
            "Authorization": f"Bearer {body['verification_token']}"
        },
    )
    assert verification_request.status_code == 409


def test_verification_token_is_bound_to_its_session(client, db):
    first_user = create_user(db, "first-verification-user")
    second_user = create_user(db, "second-verification-user")
    first_login = login(client, first_user.username, "first-device").json()
    second_login = login(client, second_user.username, "second-device").json()

    response = client.post(
        "/api/auth/verification/request",
        json={"session_id": second_login["session_id"]},
        headers={
            "Authorization": f"Bearer {first_login['verification_token']}"
        },
    )

    assert response.status_code == 401


def test_access_token_cannot_call_verification_api(client, db):
    user = create_user(db, "access-purpose-user")
    device_repository.touch_device_and_link(db, "trusted-purpose-device", user.id)
    db.commit()
    login_body = login(
        client, user.username, "trusted-purpose-device"
    ).json()

    response = client.post(
        "/api/auth/verification/request",
        json={"session_id": login_body["session_id"]},
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )

    assert response.status_code == 401


def test_verification_request_enforces_cooldown(client, db):
    user = create_user(db, "cooldown-user")
    login_body = login(client, user.username, "cooldown-device").json()
    headers = {
        "Authorization": f"Bearer {login_body['verification_token']}"
    }
    request_body = {"session_id": login_body["session_id"]}

    first_response = client.post(
        "/api/auth/verification/request",
        json=request_body,
        headers=headers,
    )
    second_response = client.post(
        "/api/auth/verification/request",
        json=request_body,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert int(second_response.headers["Retry-After"]) >= 1


def test_expired_code_is_rejected(client, db):
    user = create_user(db, "expired-code-user")
    login_body = login(client, user.username, "expired-code-device").json()
    headers = {
        "Authorization": f"Bearer {login_body['verification_token']}"
    }
    issued = client.post(
        "/api/auth/verification/request",
        json={"session_id": login_body["session_id"]},
        headers=headers,
    )
    code = issued.json()["verification_code"]

    user_session = db.get(UserSession, login_body["session_id"])
    user_session.verification_expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    db.commit()

    response = client.post(
        "/api/auth/verification/confirm",
        json={"session_id": login_body["session_id"], "code": code},
        headers=headers,
    )

    assert response.status_code == 410


def test_pending_session_cannot_use_forged_access_token(client, db):
    owner = create_user(db, "pending-token-owner")
    user = create_user(db, "pending-token-user")
    device_repository.touch_device_and_link(db, "pending-shared-device", owner.id)
    db.commit()
    login_body = login(
        client, user.username, "pending-shared-device"
    ).json()
    forged_access_token = auth_service.create_access_token(
        user.id, login_body["session_id"]
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_access_token}"},
    )

    assert response.status_code == 403
