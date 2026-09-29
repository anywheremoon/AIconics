from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transaction_score_schema import (
    TransactionRiskRequest,
    TransactionRiskResponse,
)
from app.services.auth_service import get_current_user
from app.services.transaction_risk_engine import calculate_transaction_risk


router = APIRouter(prefix="/api/risks", tags=["Transaction Risk"])


@router.post("/transaction", response_model=TransactionRiskResponse)
def assess_transaction_risk(
    data: TransactionRiskRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculate_transaction_risk(db, current_user.id, data)
