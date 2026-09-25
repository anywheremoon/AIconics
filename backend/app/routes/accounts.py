from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.account_schema import AccountResponse
from app.services.account_service import get_my_account
from app.services.auth_service import get_current_user


router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get("/me", response_model=AccountResponse)
def read_my_account(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    account = get_my_account(db, current_user.id)
    return {
        "id": account.id,
        "user_id": account.user_id,
        "username": current_user.username,
        "account_number": account.account_number,
        "balance": account.balance,
        "status": account.status,
        "opened_at": account.opened_at,
    }