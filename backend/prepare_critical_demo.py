import main
from types import SimpleNamespace
from eth_account import Account
from sqlalchemy import text
from app.database import SessionLocal
from app.services.eth_vault_service import _risk_result

db = SessionLocal()
try:
    user_id = db.execute(
        text("SELECT id FROM users WHERE username = :name"),
        {"name": "hyem07"},
    ).scalar_one()

    session_id = input("Current browser session_id: ").strip()

    active = db.execute(text("""
        SELECT session_id
        FROM user_sessions
        WHERE user_id = :user_id
          AND session_id = :session_id
          AND is_active = true
    """), {
        "user_id": user_id,
        "session_id": session_id,
    }).first()

    if active is None:
        raise RuntimeError("Active session not found")

    recipient = Account.create().address
    data = SimpleNamespace(
        session_id=session_id,
        recipient_address=recipient,
        amount_wei=str(10 * 10**18),
    )
    result = _risk_result(db, user_id=user_id, data=data)

    print("EXPECTED_RISK:", result.risk_level)
    print("EXPECTED_SCORE:", result.final_risk_score)

    if result.risk_level == "CRITICAL":
        print("TEST_RECIPIENT:", recipient)
        print("AMOUNT_ETH: 10")
    else:
        print("STOP: Do not deposit")
finally:
    db.rollback()
    db.close()
