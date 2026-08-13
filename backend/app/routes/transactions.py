from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transaction_schema import (
    TransactionResponse,
    TransferRequest,
    WithdrawRequest,
)
from app.services import account_service
from app.services.auth_service import get_current_user


router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
def read_transactions(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return account_service.list_my_transactions(db, current_user.id)


@router.post("/transfer", response_model=TransactionResponse)
def transfer_money(
    data: TransferRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_service.transfer(db, current_user.id, data)


@router.post("/withdraw", response_model=TransactionResponse)
def withdraw_money(
    data: WithdrawRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_service.withdraw(db, current_user.id, data)
