from getpass import getpass
from uuid import uuid4

import requests
from sqlalchemy import text
from app.database import engine

BASE = "http://127.0.0.1:8000"
username = input("Username: ").strip()
password = getpass("Password: ")

def login(device_id):
    response = requests.post(
        f"{BASE}/api/auth/login",
        json={
            "username": username,
            "password": password,
            "device_id": device_id,
            "location": "Seoul",
        },
        timeout=15,
    )
    print("LOGIN_HTTP:", response.status_code)
    if response.status_code != 200:
        print(response.text)
        raise SystemExit("STOP: login failed")
    return response.json()

a = login("c-binding-device-a")
b = login("c-binding-device-b")

headers_a = {
    "Authorization": f"Bearer {a['access_token']}"
}
session_b = b["session_id"]
user_id = b["user"]["id"]
request_id = str(uuid4())

checks = {
    "different_sessions": a["session_id"] != session_b,
}

# 正しい組み合わせで認証が成功することも確認する。
for label, login_result in (("A", a), ("B", b)):
    response = requests.get(
        f"{BASE}/api/auth/me",
        headers={
            "Authorization": f"Bearer {login_result['access_token']}"
        },
        timeout=15,
    )
    print(f"ME_{label}_HTTP:", response.status_code)
    checks[f"valid_token_{label}"] = response.status_code == 200

with engine.connect() as connection:
    recipient = connection.execute(
        text("""
            SELECT account_number
            FROM accounts
            WHERE user_id != :user_id
            ORDER BY id
            LIMIT 1
        """),
        {"user_id": user_id},
    ).scalar()

if recipient is None:
    raise SystemExit("STOP: recipient account is missing")

def snapshot():
    with engine.connect() as connection:
        events = connection.execute(
            text("""
                SELECT COUNT(*) FROM behavior_events
                WHERE session_id = :session_id
            """),
            {"session_id": session_b},
        ).scalar_one()

        transactions = connection.execute(
            text("""
                SELECT COUNT(*) FROM transactions
                WHERE CAST(request_id AS TEXT) = :request_id
            """),
            {"request_id": request_id},
        ).scalar_one()

        balances = connection.execute(
            text("SELECT id, balance FROM accounts ORDER BY id")
        ).all()

        session = connection.execute(
            text("""
                SELECT is_active, logout_at FROM user_sessions
                WHERE session_id = :session_id
            """),
            {"session_id": session_b},
        ).mappings().one()

    return {
        "events": events,
        "transactions": transactions,
        "balances": [(row.id, str(row.balance)) for row in balances],
        "active": session["is_active"],
        "logout_at": session["logout_at"],
    }

before = snapshot()

tests = [
    (
        "event",
        "/api/events",
        {
            "session_id": session_b,
            "device_id": "c-binding-device-b",
            "typing_speed": 8.0,
            "avg_hold_time": 100.0,
            "avg_flight_time": 80.0,
            "total_keystrokes": 20,
            "mouse_move_count": 100,
            "click_count": 3,
            "location": "Seoul",
        },
    ),
    (
        "transfer",
        "/api/transactions/transfer",
        {
            "request_id": request_id,
            "session_id": session_b,
            "recipient_account_number": recipient,
            "amount": "1.00",
        },
    ),
    (
        "logout",
        "/api/auth/logout",
        {"session_id": session_b},
    ),
]

try:
    for label, path, payload in tests:
        response = requests.post(
            BASE + path,
            headers=headers_a,
            json=payload,
            timeout=15,
        )
        print(f"{label.upper()}_HTTP:", response.status_code)
        print(f"{label.upper()}_BODY:", response.text)
        checks[f"{label}_mismatch_rejected"] = (
            response.status_code == 401
            and response.json().get("detail")
            == "Request session does not match the access token"
        )

    after = snapshot()

    checks["no_event_created"] = before["events"] == after["events"]
    checks["no_transaction_created"] = (
        before["transactions"] == after["transactions"] == 0
    )
    checks["balances_unchanged"] = before["balances"] == after["balances"]
    checks["session_b_still_active"] = (
        after["active"] is True
        and after["logout_at"] is None
    )

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("RESULT:", "PASS" if all(checks.values()) else "FAIL")

finally:
    # 각 세션은 해당 세션의 올바른 토큰으로 종료한다.
    for label, login_result in (("A", a), ("B", b)):
        response = requests.post(
            f"{BASE}/api/auth/logout",
            headers={
                "Authorization": f"Bearer {login_result['access_token']}"
            },
            json={"session_id": login_result["session_id"]},
            timeout=15,
        )
        print(f"CLEANUP_{label}_HTTP:", response.status_code)
