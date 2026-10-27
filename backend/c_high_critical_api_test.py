import math
import secrets
from uuid import uuid4

import requests
from sqlalchemy import MetaData, Table, text

from app.database import engine


BASE = "http://127.0.0.1:8000"
RUN_ID = uuid4().hex[:12]
PASSWORD = secrets.token_urlsafe(24)
INITIAL_BALANCE = "6000000.00"

metadata = MetaData()
events = Table(
    "behavior_events",
    metadata,
    autoload_with=engine,
)

sessions = []
results = []


def create_user(label):
    username = f"c217_{label}_{RUN_ID}"
    device_id = f"c217-device-{label}-{RUN_ID}"

    response = requests.post(
        f"{BASE}/api/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "device_id": device_id,
            "location": "Seoul",
        },
        timeout=30,
    )

    print(
        f"REGISTER_{label.upper()}_HTTP:",
        response.status_code,
    )

    if response.status_code != 201:
        print(response.text)
        raise RuntimeError("Registration failed")

    return username, device_id, response.json()["id"]


def login(username, device_id):
    response = requests.post(
        f"{BASE}/api/auth/login",
        json={
            "username": username,
            "password": PASSWORD,
            "device_id": device_id,
            "location": "Seoul",
        },
        timeout=30,
    )

    print("LOGIN_HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise RuntimeError("Login failed")

    result = response.json()
    sessions.append(result)
    return result


def account_for(user_id):
    with engine.connect() as connection:
        account = connection.execute(
            text("""
                SELECT id, account_number, balance, status
                FROM accounts
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        ).mappings().one()

        return dict(account)


def balances(sender_id, recipient_id):
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT id, balance
                FROM accounts
                WHERE id IN (:sender_id, :recipient_id)
                ORDER BY id
            """),
            {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
            },
        ).all()

        return [
            (row.id, str(row.balance))
            for row in rows
        ]


def run_case(label, recipient):
    username, device_id, user_id = create_user(
        label.lower()
    )
    auth = login(username, device_id)
    sender = account_for(user_id)

    amount = (
        "1.00" if label == "HIGH"
        else "5000000.00"
    )

    expected_transaction_score = (
        45.0 if label == "HIGH"
        else 85.0
    )

    expected_final_score = (
        80.75 if label == "HIGH"
        else 94.75
    )

    expected_status = (
        "PENDING_REVIEW" if label == "HIGH"
        else "ACCOUNT_REVIEW"
    )

    fixture_reasons = [
        {
            "reason_code": "TEST_BEHAVIOR_FIXTURE",
            "description": (
                "Controlled behavior fixture for API test"
            ),
            "score_type": "BEHAVIOR",
            "score_contribution": 65.0,
        },
        {
            "reason_code": "TEST_IDENTITY_FIXTURE",
            "description": (
                "Controlled identity fixture for API test"
            ),
            "score_type": "IDENTITY",
            "score_contribution": 80.0,
        },
    ]

    # 새 테스트 계정에만 잔액과 행동 기록을 구성한다.
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE accounts
                SET balance = :balance
                WHERE id = :account_id
                  AND user_id = :user_id
            """),
            {
                "balance": INITIAL_BALANCE,
                "account_id": sender["id"],
                "user_id": user_id,
            },
        )

        connection.execute(
            events.insert().values(
                user_id=str(user_id),
                session_id=auth["session_id"],
                device_id=device_id,
                ip_address="127.0.0.1",
                location="Seoul",
                typing_speed=8.0,
                avg_hold_time=100.0,
                avg_flight_time=80.0,
                total_keystrokes=20,
                mouse_move_count=100,
                click_count=3,
                is_new_device=True,
                profile_deviation_score=100.0,
                detect_anomaly=True,
                behavior_score=65.0,
                identity_score=80.0,
                baseline_status="SUFFICIENT_DATA",
                reasons=fixture_reasons,
                risk_score=100.0,
                risk_level="HIGH",
            )
        )

    request_id = str(uuid4())
    before = balances(
        sender["id"],
        recipient["id"],
    )

    response = requests.post(
        f"{BASE}/api/transactions/transfer",
        headers={
            "Authorization": (
                f"Bearer {auth['access_token']}"
            ),
        },
        json={
            "request_id": request_id,
            "session_id": auth["session_id"],
            "recipient_account_number": (
                recipient["account_number"]
            ),
            "amount": amount,
        },
        timeout=30,
    )

    print(f"\n[{label}]")
    print("TRANSFER_HTTP:", response.status_code)
    print("TRANSFER_BODY:", response.text)

    after = balances(
        sender["id"],
        recipient["id"],
    )

    with engine.connect() as connection:
        transactions = connection.execute(
            text("""
                SELECT id, status, amount,
                       sender_account_id,
                       recipient_account_id
                FROM transactions
                WHERE CAST(request_id AS TEXT) = :request_id
            """),
            {"request_id": request_id},
        ).mappings().all()

        assessments = []
        factors = []

        if len(transactions) == 1:
            assessments = connection.execute(
                text("""
                    SELECT *
                    FROM risk_assessments
                    WHERE transaction_id = :transaction_id
                """),
                {
                    "transaction_id": transactions[0]["id"],
                },
            ).mappings().all()

        if len(assessments) == 1:
            factors = connection.execute(
                text("""
                    SELECT score_type,
                           reason_code,
                           score_contribution
                    FROM risk_factors
                    WHERE risk_assessment_id = :assessment_id
                """),
                {
                    "assessment_id": assessments[0]["id"],
                },
            ).mappings().all()

    transaction = (
        transactions[0]
        if len(transactions) == 1
        else None
    )

    assessment = (
        assessments[0]
        if len(assessments) == 1
        else None
    )

    expected_factors = {
        ("BEHAVIOR", "TEST_BEHAVIOR_FIXTURE"): 65.0,
        ("IDENTITY", "TEST_IDENTITY_FIXTURE"): 80.0,
        ("TRANSACTION", "NEW_ACCOUNT"): 20.0,
        ("TRANSACTION", "NEW_RECIPIENT"): 15.0,
        (
            "TRANSACTION",
            "TRANSFER_SHORTLY_AFTER_LOGIN",
        ): 10.0,
    }

    if label == "CRITICAL":
        expected_factors.update({
            (
                "TRANSACTION",
                "HIGH_AMOUNT_TRANSFER",
            ): 30.0,
            (
                "TRANSACTION",
                "NEW_ACCOUNT_HIGH_AMOUNT",
            ): 10.0,
        })

    actual_factors = {
        (
            row["score_type"],
            row["reason_code"],
        ): float(row["score_contribution"])
        for row in factors
    }

    checks = {
        "api_success": response.status_code == 200,
        "one_transaction_saved": (
            len(transactions) == 1
        ),
        "correct_transaction_status": (
            transaction is not None
            and transaction["status"] == expected_status
        ),
        "correct_accounts_and_amount": (
            transaction is not None
            and transaction["sender_account_id"]
            == sender["id"]
            and transaction["recipient_account_id"]
            == recipient["id"]
            and str(transaction["amount"]) == amount
        ),
        "one_linked_assessment": (
            len(assessments) == 1
        ),
        "correct_risk_level_and_decision": (
            assessment is not None
            and assessment["risk_level"] == label
            and assessment["decision"] == expected_status
        ),
        "correct_scores": (
            assessment is not None
            and assessment["behavior_score"] == 65.0
            and assessment["identity_score"] == 80.0
            and assessment["transaction_score"]
            == expected_transaction_score
            and math.isclose(
                assessment["final_risk_score"],
                expected_final_score,
                abs_tol=0.000001,
            )
        ),
        "correct_saved_factors": (
            actual_factors == expected_factors
            and len(factors) == len(expected_factors)
        ),
        "both_balances_unchanged": before == after,
    }

    if assessment is not None:
        print(
            "TRANSACTION_SCORE:",
            assessment["transaction_score"],
        )
        print(
            "FINAL_SCORE:",
            assessment["final_risk_score"],
        )
        print("RISK_LEVEL:", assessment["risk_level"])
        print("DECISION:", assessment["decision"])

    print("BALANCES_BEFORE:", before)
    print("BALANCES_AFTER:", after)
    print("FACTOR_COUNT:", len(factors))

    for name, passed in checks.items():
        print(
            f"{name}: {'PASS' if passed else 'FAIL'}"
        )

    passed = all(checks.values())
    print(
        f"{label}_RESULT:",
        "PASS" if passed else "FAIL",
    )
    results.append(passed)

    if not passed:
        raise RuntimeError(
            f"{label} test failed; stopping"
        )


try:
    _, _, recipient_user_id = create_user("recipient")
    recipient = account_for(recipient_user_id)

    print("TEST_RUN:", RUN_ID)

    run_case("HIGH", recipient)
    run_case("CRITICAL", recipient)

    print(
        "\nOVERALL_RESULT:",
        (
            "PASS"
            if len(results) == 2 and all(results)
            else "FAIL"
        ),
    )

finally:
    # 검증 기록은 남기고 테스트 로그인 세션만 종료한다.
    for auth in sessions:
        try:
            response = requests.post(
                f"{BASE}/api/auth/logout",
                headers={
                    "Authorization": (
                        f"Bearer {auth['access_token']}"
                    ),
                },
                json={
                    "session_id": auth["session_id"],
                },
                timeout=15,
            )

            print(
                "CLEANUP_LOGOUT_HTTP:",
                response.status_code,
            )

        except requests.RequestException as error:
            print(
                "CLEANUP_LOGOUT_ERROR:",
                type(error).__name__,
            )