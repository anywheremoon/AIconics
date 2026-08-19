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


def test_insufficient_balance(client):
    sender_id, sender_account_id = create_user_with_account(
        "sender",
        "111111111111",
        balance=5000,
    )

    create_user_with_account(
        "recipient",
        "222222222222",
        balance=100000,
    )

    authenticate_as(sender_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "insufficient-balance-001",
            "recipient_account_number": "222222222222",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 400

    db = TestingSessionLocal()
    sender = db.query(Account).filter(
        Account.id == sender_account_id
    ).first()

    assert float(sender.balance) == 5000.00

    db.close()


def test_zero_amount_transfer(client):
    sender_id, _ = create_user_with_account(
        "sender",
        "333333333333",
    )

    create_user_with_account(
        "recipient",
        "444444444444",
    )

    authenticate_as(sender_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "zero-amount-001",
            "recipient_account_number": "444444444444",
            "amount": "0.00",
        },
    )

    assert response.status_code == 422


def test_negative_amount_transfer(client):
    sender_id, _ = create_user_with_account(
        "sender",
        "555555555555",
    )

    create_user_with_account(
        "recipient",
        "666666666666",
    )

    authenticate_as(sender_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "negative-amount-001",
            "recipient_account_number": "666666666666",
            "amount": "-1000.00",
        },
    )

    assert response.status_code == 422


def test_transfer_to_same_account(client):
    user_id, _ = create_user_with_account(
        "user01",
        "777777777777",
    )

    authenticate_as(user_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "same-account-001",
            "recipient_account_number": "777777777777",
            "amount": "1000.00",
        },
    )

    assert response.status_code == 400


def test_transfer_to_nonexistent_account(client):
    user_id, _ = create_user_with_account(
        "user01",
        "888888888888",
    )

    authenticate_as(user_id)

    response = client.post(
        "/api/transactions/transfer",
        json={
            "request_id": "missing-recipient-001",
            "recipient_account_number": "999999999999",
            "amount": "1000.00",
        },
    )

    assert response.status_code == 404


def test_duplicate_request_id_does_not_double_charge(client):
    sender_id, sender_account_id = create_user_with_account(
        "sender",
        "121212121212",
        balance=100000,
    )

    _, recipient_account_id = create_user_with_account(
        "recipient",
        "343434343434",
        balance=100000,
    )

    authenticate_as(sender_id)

    request_data = {
        "request_id": "duplicate-request-001",
        "recipient_account_number": "343434343434",
        "amount": "10000.00",
    }

    first_response = client.post(
        "/api/transactions/transfer",
        json=request_data,
    )

    second_response = client.post(
        "/api/transactions/transfer",
        json=request_data,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409

    db = TestingSessionLocal()

    sender = db.query(Account).filter(
        Account.id == sender_account_id
    ).first()

    recipient = db.query(Account).filter(
        Account.id == recipient_account_id
    ).first()

    transaction_count = db.query(Transaction).filter(
        Transaction.request_id == "duplicate-request-001"
    ).count()

    assert float(sender.balance) == 90000.00
    assert float(recipient.balance) == 110000.00
    assert transaction_count == 1

    db.close()