from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transaction_schema import (
    TransactionResponse,
    TransferRequest,
    WithdrawRequest,
    WithdrawResponse,
)
from app.services import account_service
from app.services.assessed_transfer_service import (
    assess_and_execute_transfer,
)
from app.services.auth_service import (
    get_current_user,
    require_matching_token_session,
)


router = APIRouter(
    prefix="/api/transactions",
    tags=["Transactions"],
)


@router.get(
    "",
    response_model=list[TransactionResponse],
)
def read_transactions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_service.list_my_transactions(
        db,
        current_user.id,
    )


@router.post(
    "/transfer",
    response_model=TransactionResponse,
)
def transfer_money(
    data: TransferRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 요청의 세션 ID와 JWT의 세션 ID를 비교한다.
    require_matching_token_session(
        request,
        str(data.session_id),
    )

    return assess_and_execute_transfer(
        db,
        user_id=current_user.id,
        data=data,
    )


@router.post(
    "/withdraw",
    response_model=WithdrawResponse,
)
def withdraw_money(
    data: WithdrawRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_service.withdraw(
        db,
        current_user.id,
        data,
    )