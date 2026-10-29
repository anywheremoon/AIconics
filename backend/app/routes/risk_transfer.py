from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.risk_transfer_schema import RiskTransferRequest, RiskTransferResponse
from app.services.auth_service import get_current_user
from app.services.risk_transfer_service import RiskTransferService
from app.services.transfer_signature_service import (
    SignatureConfigurationError,
    TransferSignatureService,
)


router = APIRouter(prefix="/api/risk-transfers", tags=["Risk Transfer"])


@lru_cache
def get_risk_transfer_service() -> RiskTransferService:
    try:
        return RiskTransferService(TransferSignatureService())
    except SignatureConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Risk transfer signer is not configured",
        ) from error


@router.post("/sign", response_model=RiskTransferResponse)
def assess_and_sign_risk_transfer(
    data: RiskTransferRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RiskTransferService = Depends(get_risk_transfer_service),
):
    return service.assess_and_sign(
        db,
        user_id=current_user.id,
        request=data,
    )
