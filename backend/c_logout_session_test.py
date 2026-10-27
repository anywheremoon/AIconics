from getpass import getpass
from uuid import uuid4

import requests
from sqlalchemy import text
from app.database import engine

BASE = "http://127.0.0.1:8000"

username = input("Username: ").strip()
password = getpass("Password: ")

response = requests.post(
    f"{BASE}/api/auth/login",
    json={
        "username": username,
        "password": password,
        "device_id": "c-logout-test-device",
        "location": "Seoul",
    },
    timeout=15,
)
print("LOGIN_HTTP:", response.status_code)
if response.status_code != 200:
    print(response.text)
    raise SystemExit("STOP: login failed")

login = response.json()
user_id = login["user"]["id"]
session_id = login["session_id"]
headers = {"Authorization": f"Bearer {login['access_token']}"}
request_id = str(uuid4())

with engine.connect() as connection:
    sender = connection.execute(
        text("""
            SELECT id, account_number, balance
            FROM accounts
            WHERE user_id = :user_id
            ORDER BY id
            LIMIT 1
        """),
        {"user_id": user_id},
    ).mappings().first()

    recipient = connection.execute(
        text("""
            SELECT id, account_number, balance
            FROM accounts
            WHERE user_id != :user_id
            ORDER BY id
            LIMIT 1
        """),
        {"user_id": user_id},
    ).mappings().first()

if sender is None or recipient is None:
    raise SystemExit("STOP: sender or recipient account is missing")

account_ids = {
    "sender_id": sender["id"],
    "recipient_id": recipient["id"],
}

def snapshot():
    with engine.connect() as connection:
        balances = connection.execute(
            text("""
                SELECT id, balance
                FROM accounts
                WHERE id IN (:sender_id, :recipient_id)
                ORDER BY id
            """),
            account_ids,
        ).all()

        transaction_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM transactions
                WHERE CAST(request_id AS TEXT) = :request_id
            """),
            {"request_id": request_id},
        ).scalar_one()

    return {
        "balances": [(row.id, str(row.balance)) for row in balances],
        "request_transactions": transaction_count,
    }

before = snapshot()

response = requests.post(
    f"{BASE}/api/auth/logout",
    headers=headers,
    json={"session_id": session_id},
    timeout=15,
)
print("LOGOUT_HTTP:", response.status_code)
if response.status_code != 204:
    print(response.text)
    raise SystemExit("STOP: logout failed")

with engine.connect() as connection:
    session = connection.execute(
        text("""
            SELECT is_active, logout_at
            FROM user_sessions
            WHERE session_id = :session_id AND user_id = :user_id
        """),
        {"session_id": session_id, "user_id": user_id},
    ).mappings().one()

print("SESSION_IS_ACTIVE:", session["is_active"])
print("LOGOUT_AT_SET:", session["logout_at"] is not None)

response = requests.post(
    f"{BASE}/api/transactions/transfer",
    headers=headers,
    json={
        "request_id": request_id,
        "session_id": session_id,
        "recipient_account_number": recipient["account_number"],
        "amount": "1.00",
    },
    timeout=15,
)
print("TRANSFER_HTTP:", response.status_code)
print("TRANSFER_BODY:", response.text)

after = snapshot()

checks = {
    "session_ended": (
        session["is_active"] is False
        and session["logout_at"] is not None
    ),
    "transfer_rejected_401": response.status_code == 401,
    "no_transaction_created": (
        before["request_transactions"] == 0
        and after["request_transactions"] == 0
    ),
    "both_balances_unchanged": before["balances"] == after["balances"],
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print("RESULT:", "PASS" if all(checks.values()) else "FAIL")
