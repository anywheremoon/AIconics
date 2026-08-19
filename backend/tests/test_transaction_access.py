from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.account_model import Account
from app.models.transaction_model import Transaction
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
    balance=100000,
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
        balance=balance,
    )

    db.add(account)
    db.commit()

    user_id = user.id
    account_id = account.id

    db.close()

    return user_id, account_id


def authenticate_as(user_id: int):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=user_id)
    )


def test_transaction_access_without_token(client):
    response = client.get("/api/transactions")

    assert response.status_code == 401


def test_user_can_only_view_own_transactions(client):
    user1_id, account1_id = create_user_with_account(
        "user01",
        "111111111111",
    )

    user2_id, account2_id = create_user_with_account(
        "user02",
        "222222222222",
    )

    db = TestingSessionLocal()

    db.add(
        Transaction(
            request_id="transaction-user1",
            sender_account_id=account1_id,
            recipient_account_id=None,
            transaction_type="WITHDRAW",
            amount=1000,
            status="COMPLETED",
        )
    )

    db.add(
        Transaction(
            request_id="transaction-user2",
            sender_account_id=account2_id,
            recipient_account_id=None,
            transaction_type="WITHDRAW",
            amount=2000,
            status="COMPLETED",
        )
    )

    db.commit()
    db.close()

    authenticate_as(user1_id)

    response = client.get("/api/transactions")

    assert response.status_code == 200

    request_ids = {
        item["request_id"]
        for item in response.json()
    }

    assert "transaction-user1" in request_ids
    assert "transaction-user2" not in request_ids


def test_other_users_transactions_are_not_exposed(client):
    user1_id, _ = create_user_with_account(
        "user01",
        "333333333333",
    )

    _, account2_id = create_user_with_account(
        "user02",
        "444444444444",
    )

    db = TestingSessionLocal()

    db.add(
        Transaction(
            request_id="private-user2-transaction",
            sender_account_id=account2_id,
            recipient_account_id=None,
            transaction_type="WITHDRAW",
            amount=3000,
            status="COMPLETED",
        )
    )

    db.commit()
    db.close()

    authenticate_as(user1_id)

    response = client.get("/api/transactions")

    assert response.status_code == 200

    request_ids = {
        item["request_id"]
        for item in response.json()
    }

    assert "private-user2-transaction" not in request_ids


def test_withdraw_from_own_account(client):
    user_id, account_id = create_user_with_account(
        "user01",
        "555555555555",
        balance=100000,
    )

    authenticate_as(user_id)

    response = client.post(
        "/api/transactions/withdraw",
        json={
            "request_id": "00000000-0000-4000-8000-000000000001",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200

    db = TestingSessionLocal()
    account = db.query(Account).filter(Account.id == account_id).first()

    assert float(account.balance) == 90000.00

    db.close()


def test_transfer_to_another_user(client):
    sender_id, sender_account_id = create_user_with_account(
        "sender",
        "666666666666",
        balance=100000,
    )

    _, recipient_account_id = create_user_with_account(
        "recipient",
        "777777777777",
        balance=100000,
    )

    authenticate_as(sender_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "00000000-0000-4000-8000-000000000002",
            "recipient_account_number": "777777777777",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200

    db = TestingSessionLocal()

    sender = (
        db.query(Account)
        .filter(Account.id == sender_account_id)
        .first()
    )

    recipient = (
        db.query(Account)
        .filter(Account.id == recipient_account_id)
        .first()
    )

    assert float(sender.balance) == 90000.00
    assert float(recipient.balance) == 110000.00

    db.close()
