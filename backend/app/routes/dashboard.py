from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.event_model import Event
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.models.user_session_model import UserSession


router = APIRouter(
    prefix="/api",
    tags=["Dashboard"],
)


@router.get("/admin/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    # 전체 사용자 수
    total_users = db.query(User).count()

    # 현재 모델에는 is_active가 없으므로 전체 세션 수
    total_sessions = db.query(UserSession).count()

    # 전체 이벤트 수
    total_events = db.query(Event).count()

    # MEDIUM / HIGH 위험 이벤트 수
    risky_events = (
        db.query(Event)
        .filter(Event.risk_score >= 40)
        .count()
    )

    # HIGH 상태인 사용자의 수
    high_risk_users = (
        db.query(func.count(func.distinct(Event.user_id)))
        .filter(Event.risk_score >= 70)
        .scalar()
        or 0
    )

    # 전체 거래 수
    total_transactions = db.query(Transaction).count()

    # 최근 이벤트 5건
    recent_events = (
        db.query(Event)
        .order_by(Event.created_at.desc())
        .limit(5)
        .all()
    )

    # 최근 거래 5건
    recent_transactions = (
        db.query(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "total_events": total_events,
        "risky_events": risky_events,
        "high_risk_users": high_risk_users,
        "total_transactions": total_transactions,

        "recent_events": [
            {
                "id": event.id,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "device_id": event.device_id,
                "risk_score": event.risk_score,
                "risk_level": event.risk_level,
                "detect_anomaly": event.detect_anomaly,
                "created_at": event.created_at,
            }
            for event in recent_events
        ],

        "recent_transactions": [
            {
                "id": transaction.id,
                "request_id": transaction.request_id,
                "transaction_type": transaction.transaction_type,
                "sender_account_id": transaction.sender_account_id,
                "recipient_account_id": transaction.recipient_account_id,
                "amount": float(transaction.amount),
                "status": transaction.status,
                "created_at": transaction.created_at,
            }
            for transaction in recent_transactions
        ],
    }