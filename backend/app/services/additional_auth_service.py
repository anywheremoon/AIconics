import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user_session_model import UserSession
from app.services import auth_service


VERIFICATION_CODE_TTL_SECONDS = int(
    os.getenv("VERIFICATION_CODE_TTL_SECONDS", "300")
)
VERIFICATION_REQUEST_COOLDOWN_SECONDS = int(
    os.getenv("VERIFICATION_REQUEST_COOLDOWN_SECONDS", "30")
)
VERIFICATION_MAX_ATTEMPTS = int(
    os.getenv("VERIFICATION_MAX_ATTEMPTS", "5")
)


def expose_code_in_response() -> bool:
    """Expose a code only when a local/test environment explicitly opts in."""
    return os.getenv("EXPOSE_VERIFICATION_CODE", "").lower() in {
        "1",
        "true",
        "yes",
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_db_datetime(value: datetime) -> datetime:
    # SQLite test databases can return naive datetimes even for timezone=True.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _code_hash(session_id: str, code: str) -> str:
    return hmac.new(
        auth_service.JWT_SECRET.encode(),
        f"{session_id}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def get_limited_session(
    db: Session,
    token: str,
    session_id: str,
    *,
    allow_pending: bool = False,
) -> UserSession:
    claims = auth_service.verify_verification_token(token)
    if claims["session_id"] != session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verification token does not match the session",
        )

    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == session_id,
            UserSession.user_id == claims["user_id"],
        )
        .populate_existing()
        .first()
    )
    if (
        user_session is None
        or not user_session.is_active
        or user_session.logout_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or ended login session",
        )

    allowed = {"REQUIRE_VERIFICATION"}
    if allow_pending:
        allowed.add("PENDING")
    if user_session.auth_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The session is not awaiting verification",
        )
    return user_session


def issue_code(db: Session, user_session: UserSession) -> tuple[str, int]:
    now = _now()
    if user_session.verification_requested_at is not None:
        requested_at = _normalize_db_datetime(
            user_session.verification_requested_at
        )
        retry_at = requested_at + timedelta(
            seconds=VERIFICATION_REQUEST_COOLDOWN_SECONDS
        )
        if retry_at > now:
            retry_after = max(1, int((retry_at - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Please wait before requesting another code",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

    code = f"{secrets.randbelow(1_000_000):06d}"
    user_session.verification_code_hash = _code_hash(
        user_session.session_id, code
    )
    user_session.verification_requested_at = now
    user_session.verification_expires_at = now + timedelta(
        seconds=VERIFICATION_CODE_TTL_SECONDS
    )
    user_session.verification_attempts = 0
    db.flush()
    return code, VERIFICATION_CODE_TTL_SECONDS


def confirm_code(
    db: Session, user_session: UserSession, code: str
) -> str:
    now = _now()
    if (
        user_session.verification_code_hash is None
        or user_session.verification_expires_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request a verification code first",
        )

    expires_at = _normalize_db_datetime(user_session.verification_expires_at)
    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The verification code has expired",
        )

    if user_session.verification_attempts >= VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts",
        )

    if not hmac.compare_digest(
        user_session.verification_code_hash,
        _code_hash(user_session.session_id, code),
    ):
        user_session.verification_attempts += 1
        if user_session.verification_attempts >= VERIFICATION_MAX_ATTEMPTS:
            user_session.auth_status = "PENDING"
            reasons = list(user_session.auth_reason_codes or [])
            if "TOO_MANY_VERIFICATION_ATTEMPTS" not in reasons:
                reasons.append("TOO_MANY_VERIFICATION_ATTEMPTS")
            user_session.auth_reason_codes = reasons
        db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    user_session.auth_status = "AUTHENTICATED"
    user_session.auth_reason_codes = []
    user_session.verification_code_hash = None
    user_session.verification_expires_at = None
    user_session.verification_requested_at = None
    user_session.verification_attempts = 0
    db.flush()
    return auth_service.create_access_token(
        user_session.user_id, user_session.session_id
    )
