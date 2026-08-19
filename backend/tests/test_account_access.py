from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.account_model import Account
from app.models.user_model import User
from app.services.auth_service import get_current_user
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


def create_user_with_account(
    username: str,
    account_number: str,
):
    db = TestingSessionLocal()

    user = User(
        username=username,
        password_hash="test-password-hash",
    )

    db.add(user)
    db.flush()

    account = Account(
        user_id=user.id,
        account_number=account_number,
        balance=100000,
    )

    db.add(account)
    db.commit()

    user_id = user.id

    db.close()

    return user_id


def authenticate_as(user_id: int):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )


def test_account_access_without_token(client):
    response = client.get("/api/accounts/me")

    assert response.status_code == 401


def test_account_access_with_invalid_token(client):
    response = client.get(
        "/api/accounts/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_user_can_access_own_account(client):
    user_id = create_user_with_account(
        "user01",
        "111111111111",
    )

    authenticate_as(user_id)

    response = client.get("/api/accounts/me")

    assert response.status_code == 200
    assert response.json()["account_number"] == "111111111111"


def test_admin_can_access_own_account(client):
    admin_id = create_user_with_account(
        "admin",
        "222222222222",
    )

    authenticate_as(admin_id)

    response = client.get("/api/accounts/me")

    assert response.status_code == 200
    assert response.json()["account_number"] == "222222222222"


def test_each_user_has_different_account_number(client):
    user1_id = create_user_with_account(
        "user01",
        "333333333333",
    )

    user2_id = create_user_with_account(
        "user02",
        "444444444444",
    )

    authenticate_as(user1_id)
    response1 = client.get("/api/accounts/me")

    authenticate_as(user2_id)
    response2 = client.get("/api/accounts/me")

    assert response1.status_code == 200
    assert response2.status_code == 200

    assert (
        response1.json()["account_number"]
        != response2.json()["account_number"]
    )