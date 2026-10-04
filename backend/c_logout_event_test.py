from getpass import getpass

import requests
from sqlalchemy import text
from app.database import engine

BASE = "http://127.0.0.1:8000"
DEVICE_ID = "c-logout-event-test-device"

username = input("Username: ").strip()
password = getpass("Password: ")

response = requests.post(
    f"{BASE}/api/auth/login",
    json={
        "username": username,
        "password": password,
        "device_id": DEVICE_ID,
        "location": "Seoul",
    },
    timeout=15,
)
print("LOGIN_HTTP:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit("STOP: login failed")

login = response.json()
session_id = login["session_id"]
user_id = login["user"]["id"]
headers = {
    "Authorization": f"Bearer {login['access_token']}"
}

def event_count():
    with engine.connect() as connection:
        return connection.execute(
            text("""
                SELECT COUNT(*)
                FROM behavior_events
                WHERE session_id = :session_id
            """),
            {"session_id": session_id},
        ).scalar_one()

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
            WHERE session_id = :session_id
              AND user_id = :user_id
        """),
        {
            "session_id": session_id,
            "user_id": user_id,
        },
    ).mappings().one()

before = event_count()

response = requests.post(
    f"{BASE}/api/events",
    headers=headers,
    json={
        "session_id": session_id,
        "device_id": DEVICE_ID,
        "typing_speed": 8.0,
        "avg_hold_time": 100.0,
        "avg_flight_time": 80.0,
        "total_keystrokes": 20,
        "mouse_move_count": 100,
        "click_count": 3,
        "location": "Seoul",
    },
    timeout=15,
)

print("EVENT_HTTP:", response.status_code)
print("EVENT_BODY:", response.text)

after = event_count()
print("EVENT_COUNT_BEFORE:", before)
print("EVENT_COUNT_AFTER:", after)

checks = {
    "session_ended": (
        session["is_active"] is False
        and session["logout_at"] is not None
    ),
    "event_rejected_401": response.status_code == 401,
    "no_event_created": before == after,
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print("RESULT:", "PASS" if all(checks.values()) else "FAIL")
