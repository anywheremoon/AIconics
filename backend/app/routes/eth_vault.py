from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.repositories import eth_vault_repository
from app.schemas.eth_vault_schema import (
    EthVaultAnalyzeRequest,
    EthVaultAnalyzeResponse,
    EthVaultSignedResult,
    EthVaultSubmitResponse,
    EthVaultTransferResponse,
)
from app.services.auth_service import (
    get_current_user,
    require_matching_token_session,
)
from app.services.eth_vault_blockchain_service import (
    EthVaultBlockchainError,
    submit_risk_result,
)
from app.services.eth_vault_service import analyze_transfer, policy_for_risk
from app.services.eth_vault_signature_service import (
    EthVaultSigningError,
    build_signed_result,
)


router = APIRouter(prefix="/api/eth-vault", tags=["ETH Risk Vault"])


@router.post(
    "/analyze",
    response_model=EthVaultAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_eth_transfer(
    data: EthVaultAnalyzeRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_matching_token_session(request, str(data.session_id))
    try:
        return analyze_transfer(db, user_id=current_user.id, data=data)
    except eth_vault_repository.DuplicateVaultRequestError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except EthVaultSigningError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/requests", response_model=list[EthVaultTransferResponse])
def list_my_eth_vault_requests(
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return eth_vault_repository.list_for_user(
        db, current_user.id, limit=limit
    )


@router.get(
    "/requests/{request_id}", response_model=EthVaultTransferResponse
)
def read_my_eth_vault_request(
    request_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = eth_vault_repository.find_for_user(
        db, request_id, current_user.id
    )
    if transfer is None:
        raise HTTPException(status_code=404, detail="ETH Vault transfer not found")
    return transfer


@router.get(
    "/admin/pending", response_model=list[EthVaultTransferResponse]
)
def list_pending_admin_reviews(
    limit: int = Query(default=100, ge=1, le=200),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return eth_vault_repository.list_admin_pending(db, limit=limit)


@router.post(
    "/requests/{request_id}/submit-risk",
    response_model=EthVaultSubmitResponse,
)
def submit_transfer_risk(
    request_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = eth_vault_repository.find_for_user(
        db, request_id, current_user.id
    )
    if transfer is None:
        raise HTTPException(status_code=404, detail="ETH Vault transfer not found")
    if transfer.blockchain_tx_hash:
        raise HTTPException(
            status_code=409, detail="Risk result was already submitted"
        )
    
    deadline = transfer.signature_deadline
    if deadline is None:
        raise HTTPException(status_code=409, detail="Risk signature is unavailable")
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Risk signature has expired")

    policy = policy_for_risk(
        risk_score=transfer.risk_score,
        risk_level=transfer.risk_level,
        decision=transfer.decision,
    )
    signed_result = build_signed_result(
        request_id=transfer.request_id,
        sender_address=transfer.sender_address,
        recipient_address=transfer.recipient_address,
        amount_wei=transfer.amount_wei,
        risk_score=transfer.risk_score,
        risk_level=transfer.risk_level,
        requires_auth=policy["requires_auth"],
        requires_admin_approval=policy["requires_admin_approval"],
        timelock_until=transfer.timelock_until,
        deadline=deadline,
        analysis_hash=transfer.analysis_hash,
        nonce=transfer.nonce,
    )
    EthVaultSignedResult.model_validate(signed_result)
    try:
        submission = submit_risk_result(signed_result, transfer.signature)
        eth_vault_repository.set_blockchain_submission(
            db, transfer, submission["transaction_hash"]
        )
        db.commit()
    except EthVaultBlockchainError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception:
        db.rollback()
        raise

    return {
        "request_id": transfer.request_id,
        "transaction_hash": submission["transaction_hash"],
        "block_number": submission["block_number"],
        "status": "RISK_SUBMITTED",
    }

from app.routes.eth_vault_verification import (
    router as vault_verification_router,
)

router.include_router(vault_verification_router)