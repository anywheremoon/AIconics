import hashlib
import hmac
import math
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import eth_vault_repository as repository
from app.services import auth_service, email_service
from app.services.eth_vault_blockchain_service import (
    EthVaultBlockchainError,
    complete_transfer_auth,
    get_transfer,
)


router = APIRouter()

EXPIRES_SECONDS = 300
COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5


class IssueRequest(BaseModel):
    session_id: UUID


class ConfirmRequest(IssueRequest):
    # 형식이 틀린 시도도 서비스에서 실패 횟수에 반영한다.
    code: str


def utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def code_hash(row, session_id, code):
    # 인증 용도와 거래 정보를 모두 해시에 연결한다.
    message = ":".join([
        "eth-vault-verification",
        row.deployment_id,
        str(row.chain_id),
        row.verifying_contract.lower(),
        row.request_id.lower(),
        str(row.user_id),
        session_id,
        row.sender_address.lower(),
        row.recipient_address.lower(),
        str(int(row.amount_wei)),
        code,
    ])

    return hmac.new(
        auth_service.JWT_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def locked_transfer(db, request, request_id, session_id, user):
    auth_service.require_matching_token_session(request, session_id)

    row = repository.find_by_request_id(
        db, request_id, for_update=True
    )

    if row is None or row.user_id != user.id:
        raise HTTPException(404, "ETH Vault transfer not found")

    if str(row.session_id) != session_id:
        raise HTTPException(
            403, "Transfer belongs to a different login session"
        )

    if not row.requires_auth or row.risk_level not in {"MEDIUM", "HIGH"}:
        raise HTTPException(
            409, "This transfer is not awaiting additional authentication"
        )

    if not row.blockchain_tx_hash:
        raise HTTPException(
            409, "Submit the risk result before requesting authentication"
        )

    return row


def validate_chain(row):
    onchain = get_transfer(row.request_id)

    if (
        onchain[0].lower() != row.sender_address.lower()
        or onchain[1].lower() != row.recipient_address.lower()
        or int(onchain[2]) != int(row.amount_wei)
        or int(onchain[3]) != (
            1 if row.risk_level == "MEDIUM" else 2
        )
        or not bool(onchain[7])
    ):
        raise HTTPException(409, "On-chain transfer mismatch")

    if int(onchain[4]) not in {1, 2, 3}:
        raise HTTPException(409, "Transfer is not awaiting execution")

    # 現行コントラクトのリクエスト有効期間は24時間。
    # 아래 시간은 서버 시간이 아닌 체인 시간으로 비교한다.
    from app.services.eth_vault_blockchain_service import _connect

    w3, contract, _, _ = _connect()
    expiry = int(contract.functions.REQUEST_EXPIRY().call())
    now = int(w3.eth.get_block("latest")["timestamp"])

    if now >= int(onchain[5]) + expiry:
        raise HTTPException(409, "Transfer has expired")

    return onchain


def reject_attempt(db, detail):
    # 실패 횟수 변경을 rollback하지 않고 보존한다.
    db.commit()
    raise HTTPException(400, detail)


@router.post("/requests/{request_id}/verification/request")
def issue_transfer_verification(
    request_id: str,
    data: IssueRequest,
    request: Request,
    user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    session_id = str(data.session_id)

    try:
        row = locked_transfer(
            db, request, request_id, session_id, user
        )
        chain = validate_chain(row)

        if bool(chain[9]) or row.verification_confirmed_at:
            raise HTTPException(
                409, "Email verification is already completed"
            )

        if (row.verification_attempts or 0) >= MAX_ATTEMPTS:
            raise HTTPException(
                403, "Verification attempt limit exceeded"
            )

        if not user.email:
            raise HTTPException(
                409, "This account does not have a verification email"
            )

        now = datetime.now(timezone.utc)
        last = utc(row.verification_requested_at)

        if last:
            remaining = (
                last + timedelta(seconds=COOLDOWN_SECONDS) - now
            ).total_seconds()
            if remaining > 0:
                raise HTTPException(
                    429,
                    "Please wait before requesting another code",
                    headers={
                        "Retry-After": str(math.ceil(remaining))
                    },
                )

        code = f"{secrets.randbelow(1_000_000):06d}"

        row.verification_session_id = session_id
        row.verification_code_hash = code_hash(
            row, session_id, code
        )
        row.verification_requested_at = now
        row.verification_expires_at = now + timedelta(
            seconds=EXPIRES_SECONDS
        )

        # 재발급해도 실패 횟수는 초기화하지 않는다.
        email_service.send_verification_code(
            user.email, code, EXPIRES_SECONDS
        )
        db.commit()

        return {
            "request_id": request_id,
            "delivery_destination": email_service.mask_email(
                user.email
            ),
            "expires_in_seconds": EXPIRES_SECONDS,
            "retry_after_seconds": COOLDOWN_SECONDS,
        }

    except email_service.EmailConfigurationError as error:
        db.rollback()
        raise HTTPException(
            503, "Verification email is not configured"
        ) from error
    except email_service.EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            503, "Could not send the verification email"
        ) from error
    except EthVaultBlockchainError as error:
        db.rollback()
        raise HTTPException(503, str(error)) from error
    except Exception:
        db.rollback()
        raise


@router.post("/requests/{request_id}/verification/confirm")
def confirm_transfer_verification(
    request_id: str,
    data: ConfirmRequest,
    request: Request,
    user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    session_id = str(data.session_id)

    try:
        row = locked_transfer(
            db, request, request_id, session_id, user
        )

        if row.verification_session_id != session_id:
            raise HTTPException(
                403, "Verification session mismatch"
            )

        # 번호 검증 성공 후 체인 호출만 실패했다면 재시도 가능하다.
        if row.verification_confirmed_at is None:
            if (row.verification_attempts or 0) >= MAX_ATTEMPTS:
                raise HTTPException(
                    403, "Verification attempt limit exceeded"
                )

            if (
                not row.verification_code_hash
                or not row.verification_expires_at
            ):
                raise HTTPException(
                    400, "Request a verification code first"
                )

            now = datetime.now(timezone.utc)

            if now >= utc(row.verification_expires_at):
                row.verification_code_hash = None
                reject_attempt(db, "Verification code has expired")

            code = data.code.strip()
            valid_format = (
                len(code) == 6
                and all(c in "0123456789" for c in code)
            )

            matches = valid_format and hmac.compare_digest(
                row.verification_code_hash,
                code_hash(row, session_id, code),
            )

            if not matches:
                row.verification_attempts = (
                    row.verification_attempts or 0
                ) + 1
                reject_attempt(
                    db,
                    "Verification attempt limit exceeded"
                    if row.verification_attempts >= MAX_ATTEMPTS
                    else "Invalid verification code",
                )

            row.verification_confirmed_at = now
            row.verification_code_hash = None
            db.commit()

        # 잠금을 다시 획득하여 동일 거래의 동시 반영을 직렬화한다.
        row = locked_transfer(
            db, request, request_id, session_id, user
        )
        validate_chain(row)

        result = complete_transfer_auth(
            row.request_id,
            sender_address=row.sender_address,
            recipient_address=row.recipient_address,
            amount_wei=row.amount_wei,
        )

        if result["transaction_hash"]:
            row.auth_tx_hash = result["transaction_hash"]

        db.commit()

        return {
            "request_id": row.request_id,
            "email_verified": True,
            "onchain_auth_completed": True,
            "auth_transaction_hash": row.auth_tx_hash,
        }

    except EthVaultBlockchainError as error:
        db.rollback()
        raise HTTPException(503, str(error)) from error
    except Exception:
        db.rollback()
        raise