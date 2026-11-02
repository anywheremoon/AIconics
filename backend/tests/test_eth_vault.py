from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from eth_account import Account
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.eth_vault_model import EthVaultTransfer
from app.models.user_model import User
from app.repositories import eth_vault_repository
from app.schemas.eth_vault_schema import EthVaultAnalyzeRequest
from app.services import eth_vault_service
from app.services.eth_vault_signature_service import (
    build_analysis_hash,
    build_signed_result,
    recover_signer,
    sign_result,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

PRIVATE_KEY = "0x" + "11" * 32
CONTRACT = "0x" + "cc" * 20
SENDER = "0x" + "aa" * 20
RECIPIENT = "0x" + "bb" * 20
REQUEST_ID = "0x" + "01" * 32


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


def _user(db, username="vault-user"):
    user = User(username=username, password_hash="test", role="USER")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _request(request_id=REQUEST_ID):
    return EthVaultAnalyzeRequest(
        request_id=request_id,
        session_id=uuid4(),
        sender_address=SENDER,
        recipient_address=RECIPIENT,
        amount_wei=Decimal("100000000000000000"),
        chain_id=31337,
        verifying_contract=CONTRACT,
    )


@pytest.mark.parametrize(
    ("level", "status", "auth", "admin", "delay"),
    [
        ("LOW", "READY", False, False, 0),
        ("MEDIUM", "AUTH_REQUIRED", True, False, 0),
        ("HIGH", "ADMIN_REVIEW", True, True, 3600),
        ("CRITICAL", "REJECTED", True, True, 0),
    ],
)
def test_risk_policy_mapping(level, status, auth, admin, delay):
    policy = eth_vault_service.policy_for_risk(
        risk_score=50, risk_level=level, decision="TEST"
    )
    assert policy["status"] == status
    assert policy["requires_auth"] is auth
    assert policy["requires_admin_approval"] is admin
    assert policy["timelock_seconds"] == delay


def test_eip712_signature_recovers_configured_signer():
    deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
    digest = build_analysis_hash(
        request_id=REQUEST_ID,
        risk_score=20,
        risk_level="LOW",
        decision="APPROVED",
        reasons=[],
    )
    result = build_signed_result(
        request_id=REQUEST_ID,
        sender_address=SENDER,
        recipient_address=RECIPIENT,
        amount_wei=10**17,
        risk_score=20,
        risk_level="LOW",
        requires_auth=False,
        requires_admin_approval=False,
        timelock_until=None,
        deadline=deadline,
        analysis_hash=digest,
        nonce="0x" + "02" * 32,
    )
    signature = sign_result(
        result,
        chain_id=31337,
        verifying_contract=CONTRACT,
        private_key=PRIVATE_KEY,
    )

    assert signature.startswith("0x")
    assert len(signature) == 132
    assert recover_signer(
        result,
        signature,
        chain_id=31337,
        verifying_contract=CONTRACT,
    ) == Account.from_key(PRIVATE_KEY).address


def test_schema_rejects_self_transfer():
    with pytest.raises(ValidationError):
        EthVaultAnalyzeRequest(
            request_id=REQUEST_ID,
            session_id=uuid4(),
            sender_address=SENDER,
            recipient_address=SENDER,
            amount_wei=1,
            chain_id=31337,
            verifying_contract=CONTRACT,
        )


def test_repository_does_not_expose_another_users_transfer(db):
    owner = _user(db, "owner")
    other = _user(db, "other")
    transfer = eth_vault_repository.create_transfer(
        db,
        request_id=REQUEST_ID,
        user_id=owner.id,
        session_id=str(uuid4()),
        sender_address=SENDER,
        recipient_address=RECIPIENT,
        amount_wei=1,
        chain_id=31337,
        verifying_contract=CONTRACT,
    )
    db.commit()

    assert eth_vault_repository.find_for_user(
        db, REQUEST_ID, owner.id
    ) == transfer
    assert eth_vault_repository.find_for_user(
        db, REQUEST_ID, other.id
    ) is None


def test_analyze_transfer_persists_signed_policy(db, monkeypatch):
    user = _user(db)
    monkeypatch.setattr(
        eth_vault_service,
        "_risk_result",
        lambda *args, **kwargs: SimpleNamespace(
            final_risk_score=22.4,
            risk_level="LOW",
            decision="APPROVED",
            reasons=[],
        ),
    )

    response = eth_vault_service.analyze_transfer(
        db,
        user_id=user.id,
        data=_request(),
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        private_key=PRIVATE_KEY,
    )

    assert response["policy"]["risk_score"] == 22
    assert response["policy"]["status"] == "READY"
    assert response["transfer"].status == "READY"
    assert response["transfer"].signature == response["signature"]
    assert db.query(EthVaultTransfer).count() == 1


def test_duplicate_request_id_is_rejected_before_rescoring(db, monkeypatch):
    user = _user(db)
    data = _request()
    risk = SimpleNamespace(
        final_risk_score=22.4,
        risk_level="LOW",
        decision="APPROVED",
        reasons=[],
    )
    monkeypatch.setattr(
        eth_vault_service, "_risk_result", lambda *args, **kwargs: risk
    )
    eth_vault_service.analyze_transfer(
        db,
        user_id=user.id,
        data=data,
        private_key=PRIVATE_KEY,
    )

    with pytest.raises(
        eth_vault_repository.DuplicateVaultRequestError
    ):
        eth_vault_service.analyze_transfer(
            db,
            user_id=user.id,
            data=data,
            private_key=PRIVATE_KEY,
        )

