import main
from datetime import datetime, timezone
from sqlalchemy import MetaData, Table, select, text
from app.database import SessionLocal

db = SessionLocal()

try:
    user_id = db.execute(
        text("SELECT id FROM users WHERE username = :name"),
        {"name": "hyem07"},
    ).scalar_one()

    session_id = input(
        "Current browser session_id: "
    ).strip()

    active = db.execute(text("""
        SELECT session_id
        FROM user_sessions
        WHERE session_id = :session_id
          AND user_id = :user_id
          AND is_active = true
    """), {
        "session_id": session_id,
        "user_id": user_id,
    }).first()

    if active is None:
        raise RuntimeError("Active session not found for hyem07")

    events = Table(
        "behavior_events",
        MetaData(),
        autoload_with=db.connection(),
    )

    latest = db.execute(
        select(events)
        .where(
            events.c.user_id == str(user_id),
            events.c.session_id == session_id,
        )
        .order_by(
            events.c.created_at.desc(),
            events.c.id.desc(),
        )
        .limit(1)
    ).mappings().one_or_none()

    if latest is None:
        raise RuntimeError(
            "No event for this session. Run Agent briefly, "
            "then stop Agent and retry."
        )

    values = dict(latest)

    for column in events.primary_key.columns:
        values.pop(column.name, None)

    values.update(
        behavior_score=65.0,
        identity_score=80.0,
        reasons=[
            {
                "reason_code": "TEST_BEHAVIOR_FIXTURE",
                "description": "Local demo fixture, not measured behavior.",
                "score_type": "BEHAVIOR",
                "score_contribution": 65.0,
            },
            {
                "reason_code": "TEST_IDENTITY_FIXTURE",
                "description": "Local demo fixture, not measured identity.",
                "score_type": "IDENTITY",
                "score_contribution": 80.0,
            },
        ],
        created_at=datetime.now(timezone.utc),
    )

    if "updated_at" in values:
        values["updated_at"] = values["created_at"]

    event_id = db.execute(
        events.insert()
        .values(**values)
        .returning(events.c.id)
    ).scalar_one()

    db.commit()

    print("DEMO_EVENT_ID:", event_id)
    print("BEHAVIOR: 65 / IDENTITY: 80")
    print("READY: Keep Agent stopped and stay logged in.")

except Exception:
    db.rollback()
    raise
finally:
    db.close()
