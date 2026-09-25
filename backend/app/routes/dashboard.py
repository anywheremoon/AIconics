from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.event_model import Event
from app.models.transaction_model import Transaction
from app.models.user_model import User
from app.models.user_session_model import UserSession


router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/admin/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    recent_events = db.query(Event).order_by(Event.created_at.desc()).limit(5).all()
    recent_transactions = (
        db.query(Transaction).order_by(Transaction.created_at.desc()).limit(5).all()
    )
    return {
        "total_users": db.query(User).count(),
        "total_sessions": db.query(UserSession).count(),
        "total_events": db.query(Event).count(),
        "risky_events": db.query(Event).filter(Event.risk_score >= 40).count(),
        "high_risk_users": (
            db.query(func.count(func.distinct(Event.user_id)))
            .filter(Event.risk_score >= 70)
            .scalar()
            or 0
        ),
        "total_transactions": db.query(Transaction).count(),
        "recent_events": recent_events,
        "recent_transactions": recent_transactions,
    }
