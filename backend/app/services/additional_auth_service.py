import hashlib
import hmac
import math
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user_session_model import UserSession
from app.services import auth_service


VERIFICATION_CODE_EXPIRE_SECONDS = 300
VERIFICATION_REQUEST_COOLDOWN_SECONDS = 60
VERIFICATION_MAX_ATTEMPTS = 5


def expose_code_in_response() -> bool:
    """개발 환경에서만 인증번호를 응답에 포함한다."""
    return (
        os.getenv("APP_ENV", "").lower() in {"development", "local", "test"}
        and os.getenv("VERIFICATION_EXPOSE_CODE", "").lower() == "true"
    )


def _utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_code(session_id: str, code: str) -> str:
    """서버 비밀키와 세션 ID를 사용해 인증번호를 해시한다."""
    return hmac.new(
        auth_service.JWT_SECRET.encode("utf-8"),
        f"verification:{session_id}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _require_verification(user_session):
    if (
        not user_session.is_active
        or user_session.logout_at is not None
    ):
        raise HTTPException(
            status_code=401,
            detail="The login session has ended",
        )

    if user_session.auth_status != "REQUIRE_VERIFICATION":
        raise HTTPException(
            status_code=403,
            detail="This session is not awaiting verification",
        )


def get_limited_session(
    db: Session,
    token: str,
    session_id: str,
):
    """제한 토큰 소유자와 요청 세션을 검증하고 행 잠금을 획득한다."""
    claims = auth_service.verify_verification_token(token)

    if claims["session_id"] != session_id:
        raise HTTPException(
            status_code=403,
            detail="Verification token session mismatch",
        )

    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == session_id,
            UserSession.user_id == claims["user_id"],
        )
        .populate_existing()
        .with_for_update()
        .first()
    )

    if user_session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid login session",
        )

    if (
        not user_session.is_active
        or user_session.logout_at is not None
    ):
        raise HTTPException(
            status_code=401,
            detail="The login session has ended",
        )

    # 보류 세션은 안내 조회용으로만 사용할 수 있다.
    # 번호 발급·확인에서는 _require_verification()으로 거부한다.
    if user_session.auth_status not in {
        "REQUIRE_VERIFICATION",
        "PENDING_REVIEW",
    }:
        raise HTTPException(
            status_code=403,
            detail="Verification token is no longer usable",
        )

    return user_session


def issue_code(db: Session, user_session):
    """6자리 인증번호를 발급한다. commit은 라우트에서 수행한다."""
    _require_verification(user_session)

    attempts = user_session.verification_attempts or 0
    if attempts >= VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=403,
            detail="Verification attempt limit exceeded",
        )

    now = datetime.now(timezone.utc)
    requested_at = _utc(user_session.verification_requested_at)

    if requested_at is not None:
        remaining = (
            requested_at
            + timedelta(seconds=VERIFICATION_REQUEST_COOLDOWN_SECONDS)
            - now
        ).total_seconds()

        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail="Please wait before requesting another code",
                headers={"Retry-After": str(math.ceil(remaining))},
            )

    # 실제 발송 기능이 없는 상태에서 발급 성공으로 응답하지 않는다.
    if not expose_code_in_response():
        raise HTTPException(
            status_code=503,
            detail="Verification delivery is not configured",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"

    user_session.verification_code_hash = _hash_code(
        user_session.session_id,
        code,
    )
    user_session.verification_requested_at = now
    user_session.verification_expires_at = now + timedelta(
        seconds=VERIFICATION_CODE_EXPIRE_SECONDS
    )

    # 재발급해도 누적 실패 횟수는 초기화하지 않는다.
    db.flush()

    return code, VERIFICATION_CODE_EXPIRE_SECONDS


def confirm_code(db: Session, user_session, code: str) -> str:
    """번호를 확인하고 같은 세션을 최종 인증 상태로 전환한다."""
    _require_verification(user_session)

    attempts = user_session.verification_attempts or 0
    if attempts >= VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=403,
            detail="Verification attempt limit exceeded",
        )

    if (
        not user_session.verification_code_hash
        or user_session.verification_expires_at is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Request a verification code first",
        )

    now = datetime.now(timezone.utc)
    expires_at = _utc(user_session.verification_expires_at)

    if now >= expires_at:
        user_session.verification_code_hash = None
        user_session.verification_expires_at = None
        db.flush()

        raise HTTPException(
            status_code=400,
            detail="Verification code has expired",
        )

    valid_format = (
        isinstance(code, str)
        and len(code) == 6
        and all(char in "0123456789" for char in code)
    )

    matches = valid_format and hmac.compare_digest(
        user_session.verification_code_hash,
        _hash_code(user_session.session_id, code),
    )

    if not matches:
        user_session.verification_attempts = attempts + 1

        if user_session.verification_attempts >= VERIFICATION_MAX_ATTEMPTS:
            user_session.auth_status = "PENDING_REVIEW"
            user_session.auth_reason_codes = list(
                dict.fromkeys(
                    list(user_session.auth_reason_codes or [])
                    + ["VERIFICATION_ATTEMPTS_EXCEEDED"]
                )
            )
            user_session.verification_code_hash = None
            user_session.verification_expires_at = None

        db.flush()

        # 현재 auth.py는 400일 때 실패 횟수와 보류 상태를 commit한다.
        raise HTTPException(
            status_code=400,
            detail=(
                "Verification attempt limit exceeded; login is pending"
                if user_session.auth_status == "PENDING_REVIEW"
                else "Invalid verification code"
            ),
        )

    user_session.auth_status = "AUTHENTICATED"
    user_session.auth_reason_codes = []
    user_session.verification_code_hash = None
    user_session.verification_expires_at = None

    access_token = auth_service.create_access_token(
        user_session.user_id,
        user_session.session_id,
    )

    db.flush()
    return access_token