import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.graph.graph_repository import (
    driver,
    merge_transfer,
    merge_user_account,
)
from app.models.account_model import Account
from app.models.device_model import Device
from app.models.event_model import Event
from app.models.risk_assessment_model import RiskAssessment
from app.models.risk_factor_model import RiskFactor
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.models.user_session_model import UserSession
from app.services.auth_service import get_current_user
from main import app


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NEO4J_INTEGRATION") != "1",
    reason="Set RUN_NEO4J_INTEGRATION=1 with Neo4j running",
)


def test_real_neo4j_graph_score_is_used_and_completed_transfer_is_synced():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

    unique = uuid4().int % 10_000_000
    base_id = 1_800_000_000 + unique * 10
    sender_user_id = base_id + 1
    other_user_id = base_id + 2
    recipient_user_id = base_id + 3
    beneficiary_user_id = base_id + 4
    sender_account_id = base_id + 11
    other_account_id = base_id + 12
    recipient_account_id = base_id + 13
    beneficiary_account_id = base_id + 14
    graph_user_ids = [sender_user_id, other_user_id, beneficiary_user_id]
    graph_account_ids = [
        sender_account_id,
        other_account_id,
        recipient_account_id,
        beneficiary_account_id,
    ]
    sender_account_number = f"{unique:012d}"
    recipient_account_number = f"{unique + 1:012d}"

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    try:
        now = datetime.now(timezone.utc)
        db = session_factory()
        db.add_all(
            [
                User(id=sender_user_id, username=f"neo-sender-{unique}", password_hash="x"),
                User(id=recipient_user_id, username=f"neo-recipient-{unique}", password_hash="x"),
            ]
        )
        db.flush()
        sender = Account(
            id=sender_account_id,
            user_id=sender_user_id,
            account_number=sender_account_number,
            balance=Decimal("100000.00"),
            opened_at=now - timedelta(days=30),
        )
        recipient = Account(
            id=recipient_account_id,
            user_id=recipient_user_id,
            account_number=recipient_account_number,
            balance=Decimal("100000.00"),
            opened_at=now - timedelta(days=30),
        )
        db.add_all([sender, recipient])
        device_id = f"neo-device-{uuid4()}"
        session_id = str(uuid4())
        db.add(Device(device_id=device_id))
        db.flush()
        db.add(
            UserSession(
                session_id=session_id,
                user_id=sender_user_id,
                device_id=device_id,
                login_at=now - timedelta(hours=1),
                device_trust_status="TRUSTED_DEVICE",
                repeated_login_detected=False,
                account_switch_detected=False,
                recent_login_count=1,
                recent_device_account_count=1,
            )
        )
        db.add(
            Transaction(
                request_id=str(uuid4()),
                transaction_type="TRANSFER",
                sender_account_id=sender_account_id,
                recipient_account_id=recipient_account_id,
                amount=Decimal("1000.00"),
                status="COMPLETED",
                created_at=now - timedelta(days=2),
            )
        )
        db.add(
            Event(
                user_id=str(sender_user_id),
                session_id=session_id,
                device_id=device_id,
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
                risk_score=0,
                risk_level="LOW",
            )
        )
        db.commit()
        db.close()

        merge_user_account(sender_user_id, sender_account_id, sender_account_number)
        merge_user_account(other_user_id, other_account_id, f"{unique + 2:012d}")
        merge_user_account(
            beneficiary_user_id,
            beneficiary_account_id,
            f"{unique + 3:012d}",
        )
        merge_transfer(
            base_id + 21,
            sender_account_id,
            beneficiary_account_id,
            1000.0,
            now - timedelta(days=2),
        )
        merge_transfer(
            base_id + 22,
            other_account_id,
            beneficiary_account_id,
            1000.0,
            now - timedelta(days=2),
        )

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=sender_user_id
        )
        response = TestClient(app).post(
            "/api/transactions/transfer",
            json={
                "request_id": str(uuid4()),
                "session_id": session_id,
                "recipient_account_number": recipient_account_number,
                "amount": "1000.00",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"

        db = session_factory()
        transaction = db.query(Transaction).filter(
            Transaction.request_id == response.json()["request_id"]
        ).one()
        assessment = db.query(RiskAssessment).filter(
            RiskAssessment.transaction_id == transaction.id
        ).one()
        graph_factor = db.query(RiskFactor).filter(
            RiskFactor.risk_assessment_id == assessment.id,
            RiskFactor.score_type == "GRAPH",
        ).one()

        assert assessment.graph_score == 25
        assert assessment.final_risk_score == 5
        assert graph_factor.reason_code == "COMMON_BENEFICIARY"
        assert graph_factor.final_score_contribution == 5

        with driver.session() as neo4j_session:
            synced = neo4j_session.run(
                """
                MATCH (:Account {account_id: $sender_id})
                      -[t:TRANSFERRED_TO {transaction_id: $transaction_id}]->
                      (:Account {account_id: $recipient_id})
                RETURN count(t) AS count
                """,
                sender_id=sender_account_id,
                recipient_id=recipient_account_id,
                transaction_id=transaction.id,
            ).single()
        assert synced["count"] == 1
        db.close()
    finally:
        app.dependency_overrides.clear()
        with driver.session() as neo4j_session:
            neo4j_session.run(
                """
                MATCH (n)
                WHERE n.user_id IN $user_ids OR n.account_id IN $account_ids
                DETACH DELETE n
                """,
                user_ids=graph_user_ids,
                account_ids=graph_account_ids,
            ).consume()
        Base.metadata.drop_all(engine)
        engine.dispose()
