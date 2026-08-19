import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.repositories import user_repository
from app.services.auth_service import hash_password
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
