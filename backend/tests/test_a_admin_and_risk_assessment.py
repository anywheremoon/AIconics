from decimal import Decimal
from types import SimpleNamespace

import pytest
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.account_model import Account
from app.models.risk_assessment_model import RiskAssessment
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.repositories import user_repository
from app.services import auth_service, device_trust_service
from app.services.auth_service import get_current_user, hash_password
from app.services.risk_assessment_service import create_risk_assessment
from app.services.risk_decision_service import assess_final_risk
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
    monkeypatch.setattr(auth_service, "PASSWORD_ITERATIONS", 1_000)
    monkeypatch.setattr(auth_service, "sync_login", lambda *args: None)
    yield
    app.dependency_overrides.clear()
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


def create_user(db, username: str, *, role: str = "USER") -> User:
    user = user_repository.create_user(
        db,
        username,
        hash_password("password1234"),
    )
    if role != "USER":
        user_repository.update_role(db, user, role)
    db.commit()
    db.refresh(user)
    return user


def login(client: TestClient, username: str, device_id: str):
    return client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "password1234",
            "device_id": device_id,
            "location": "Seoul",
        },
    )


def test_admin_login_bypasses_shared_device_hold(client, db):
    existing_user = create_user(db, "existing-user")
    admin = create_user(db, "admin-user", role="ADMIN")
    shared_device_id = "shared-admin-test-device"
    device_trust_service.record_device_use(
        db,
        existing_user.id,
        shared_device_id,
    )
    db.commit()

    response = login(client, admin.username, shared_device_id)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "ADMIN"
    assert body["device_trust_status"] == "SHARED_DEVICE"
    assert body["login_status"] == "AUTHENTICATED"
    assert body["requires_verification"] is False
    assert body["reason_codes"] == []
    assert body["access_token"]
    assert body["verification_token"] is None


def test_admin_login_bypasses_new_device_verification(client, db):
    admin = create_user(db, "new-device-admin", role="ADMIN")

    response = login(client, admin.username, "brand-new-admin-device")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "ADMIN"
    assert body["device_trust_status"] == "NEW_DEVICE"
    assert body["login_status"] == "AUTHENTICATED"
    assert body["requires_verification"] is False
    assert body["reason_codes"] == []
    assert body["access_token"]
    assert body["verification_token"] is None


def test_regular_user_is_still_held_on_shared_device(client, db):
    existing_user = create_user(db, "device-owner")
    regular_user = create_user(db, "regular-user")
    shared_device_id = "shared-regular-test-device"
    device_trust_service.record_device_use(
        db,
        existing_user.id,
        shared_device_id,
    )
    db.commit()

    response = login(client, regular_user.username, shared_device_id)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "USER"
    assert body["device_trust_status"] == "SHARED_DEVICE"
    assert body["login_status"] == "PENDING_REVIEW"
    assert body["reason_codes"] == ["SHARED_DEVICE"]
    assert body["access_token"] is None
    assert body["verification_token"]


def _create_transaction(db, owner: User, request_id: str) -> Transaction:
    account = Account(
        user_id=owner.id,
        account_number=f"{owner.id:012d}",
        balance=Decimal("100000.00"),
    )
    db.add(account)
    db.flush()
    transaction = Transaction(
        request_id=request_id,
        transaction_type="WITHDRAW",
        sender_account_id=account.id,
        recipient_account_id=None,
        amount=Decimal("1000.00"),
        status="COMPLETED",
    )
    db.add(transaction)
    db.flush()
    return transaction


def test_risk_result_is_saved_and_returned_for_owned_transaction(client, db):
    owner = create_user(db, "risk-owner")
    transaction = _create_transaction(
        db,
        owner,
        "00000000-0000-4000-8000-000000000701",
    )
    result = assess_final_risk(
        behavior_score=20,
        identity_score=10,
        transaction_score=30,
        graph_score=5,
        behavior_reasons=[
            {
                "reason_code": "BEHAVIOR_DEVIATION",
                "description": "행동 패턴 편차가 감지되었습니다.",
                "score_type": "BEHAVIOR",
                "score_contribution": 20,
            }
        ],
    )

    assessment = create_risk_assessment(
        db,
        transaction_id=transaction.id,
        result=result,
    )
    db.commit()
    assessment_id = assessment.id
    transaction_id = transaction.id

    persisted = db.get(RiskAssessment, assessment_id)
    assert persisted.transaction_id == transaction_id
    assert persisted.final_risk_score == pytest.approx(
        result.final_risk_score
    )
    assert persisted.risk_level == result.risk_level
    assert persisted.decision == result.decision
    assert persisted.calculation_details["weights"] == result.applied_weights

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=owner.id,
        role="USER",
    )
    response = client.get(f"/api/risk-assessments/{transaction_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == assessment_id
    assert body["transaction_id"] == transaction_id
    assert body["final_risk_score"] == pytest.approx(
        result.final_risk_score
    )
    assert body["risk_level"] == result.risk_level
    assert body["decision"] == result.decision
    assert body["calculation_details"]["weights"] == result.applied_weights
    assert len(body["factors"]) == 1
    factor = body["factors"][0]
    assert factor["reason_code"] == "BEHAVIOR_DEVIATION"
    assert factor["description"] == "행동 패턴 편차가 감지되었습니다."
    assert factor["score_type"] == "BEHAVIOR"
    assert factor["score_contribution"] == 20.0
    assert factor["final_score_contribution"] >= 0


def test_risk_result_is_not_exposed_to_another_user(client, db):
    owner = create_user(db, "private-risk-owner")
    other_user = create_user(db, "other-risk-user")
    transaction = _create_transaction(
        db,
        owner,
        "00000000-0000-4000-8000-000000000702",
    )
    result = assess_final_risk(
        behavior_score=0,
        identity_score=0,
        transaction_score=0,
    )
    create_risk_assessment(
        db,
        transaction_id=transaction.id,
        result=result,
    )
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=other_user.id,
        role="USER",
    )
    response = client.get(f"/api/risk-assessments/{transaction.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"
