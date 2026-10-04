import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event_model import Event
from app.models.login_history_model import LoginHistory
from app.models.user_session_model import UserSession
from app.repositories import user_repository
from app.services import user_profile_service
from app.models.event_model import Event


PASSWORD_ITERATIONS = 600_000

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

JWT_SECRET = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(48)

    warnings.warn(
        "JWT_SECRET_KEY is not set; "
        "tokens will be invalid after the process restarts.",
        RuntimeWarning,
        stacklevel=2,
    )

bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(value: bytes) -> str:
    return (
        base64.urlsafe_b64encode(value)
        .rstrip(b"=")
        .decode("ascii")
    )


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(
        value + "=" * (-len(value) % 4)
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}$"
        f"{_b64encode(salt)}${_b64encode(digest)}"
    )


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    try:
        algorithm, iterations, salt, expected = (
            password_hash.split("$", 3)
        )

        if (
            algorithm != "pbkdf2_sha256"
            or int(iterations) != PASSWORD_ITERATIONS
        ):
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode(),
            _b64decode(salt),
            int(iterations),
        )

        return hmac.compare_digest(
            _b64decode(expected),
            actual,
        )

    except (ValueError, TypeError, binascii.Error):
        return False


def create_access_token(
    user_id: int,
    session_id: str,
) -> str:
    """사용자 ID와 로그인 세션 ID를 포함한 JWT를 발급한다."""
    now = datetime.now(timezone.utc)

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }

    payload = {
        "sub": str(user_id),
        "session_id": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (
                now
                + timedelta(
                    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
                )
            ).timestamp()
        ),
    }

    encoded_header = _b64encode(
        json.dumps(
            header,
            separators=(",", ":"),
        ).encode()
    )

    encoded_payload = _b64encode(
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode()
    )

    signing_input = (
        f"{encoded_header}.{encoded_payload}".encode()
    )

    signature = hmac.new(
        JWT_SECRET.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()

    return (
        f"{encoded_header}.{encoded_payload}."
        f"{_b64encode(signature)}"
    )


def _verify_access_token_claims(token: str) -> dict:
    """JWT 서명·만료·사용자 ID·세션 ID를 검증한다."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        (
            encoded_header,
            encoded_payload,
            encoded_signature,
        ) = token.split(".")

        header = json.loads(
            _b64decode(encoded_header)
        )

        if header != {
            "alg": "HS256",
            "typ": "JWT",
        }:
            raise ValueError("Unsupported JWT header")

        signing_input = (
            f"{encoded_header}.{encoded_payload}".encode()
        )

        expected = hmac.new(
            JWT_SECRET.encode(),
            signing_input,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(
            expected,
            _b64decode(encoded_signature),
        ):
            raise ValueError("Invalid signature")

        payload = json.loads(
            _b64decode(encoded_payload)
        )

        if not isinstance(payload, dict):
            raise ValueError("Invalid JWT payload")

        if int(payload["exp"]) <= int(
            datetime.now(timezone.utc).timestamp()
        ):
            raise ValueError("Expired token")

        user_id = int(payload["sub"])
        session_id = payload["session_id"]

        if (
            not isinstance(session_id, str)
            or not session_id
            or len(session_id) > 36
        ):
            raise ValueError("Invalid token session")

        return {
            "user_id": user_id,
            "session_id": session_id,
        }

    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        UnicodeDecodeError,
        binascii.Error,
    ):
        raise credentials_error


def verify_access_token(token: str) -> int:
    """기존 인터페이스에 맞춰 검증된 사용자 ID를 반환한다."""
    return _verify_access_token_claims(token)["user_id"]


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _verify_access_token_claims(
        credentials.credentials
    )

    user = user_repository.find_by_id(
        db,
        claims["user_id"],
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == claims["session_id"],
            UserSession.user_id == user.id,
        )
        .populate_existing()
        .first()
    )

    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login session",
        )

    if (
        not user_session.is_active
        or user_session.logout_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The login session has ended",
        )

    request.state.auth_session_id = claims["session_id"]

    return user


def require_matching_token_session(
    request: Request,
    session_id: str,
) -> None:
    """요청의 세션 ID가 JWT의 세션 ID와 같은지 확인한다."""
    token_session_id = getattr(
        request.state,
        "auth_session_id",
        None,
    )

    if (
        token_session_id is None
        or token_session_id != str(session_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Request session does not match "
                "the access token"
            ),
        )


def create_virtual_account(
    db: Session,
    user_id: int,
):
    """B의 계좌 생성 서비스와 연결한다."""
    try:
        from app.services.account_service import (
            create_virtual_account as account_creator,
        )

    except ModuleNotFoundError as error:
        if error.name == "app.services.account_service":
            return None
        raise

    return account_creator(db, user_id)


def register_user(
    db: Session,
    data,
    ip_address: str | None = None,
):
    if user_repository.username_exists(
        db,
        data.username,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    try:
        user = user_repository.create_user(
            db,
            data.username,
            hash_password(data.password),
        )

        account = create_virtual_account(
            db,
            user.id,
        )

        user_profile_service.create_initial_profile(
            db,
            user.id,
            data.device_id,
            ip_address,
            data.location,
        )

        db.commit()
        db.refresh(user)

        if account is not None:
            db.refresh(account)

        sync_registration(user, account)

        return user

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from error

    except Exception:
        db.rollback()
        raise


def _save_login_history(
    db: Session,
    user_id: int | None,
    device_id: str | None,
    ip_address: str | None,
    success: bool,
):
    db.add(
        LoginHistory(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            success=success,
        )
    )

    db.commit()


def login_user(
    db: Session,
    data,
    device_id: str | None = None,
    ip_address: str | None = None,
):
    """
    로그인 자격을 확인하고 이력을 기록한다.
    JWT는 로그인 라우트에서 세션 생성 후 발급한다.
    """
    user = user_repository.find_by_username(
        db,
        data.username,
    )

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        _save_login_history(
            db,
            user.id if user else None,
            device_id,
            ip_address,
            False,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _save_login_history(
        db,
        user.id,
        device_id,
        ip_address,
        True,
    )

    sync_login(
        user.id,
        device_id,
        ip_address,
    )

    return {
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }


def delete_user_account(
    db: Session,
    user,
) -> None:
    user_id = user.id

    try:
        # 1. 사용자 이벤트 삭제
        db.query(Event).filter(
            Event.user_id == str(user_id)
        ).delete(synchronize_session=False)

        # 2. 사용자 세션 삭제
        db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).delete(synchronize_session=False)

        user_repository.delete_user(db, user)

        # 8. DB 반영
        db.commit()

    except Exception:
        db.rollback()
        raise

    # 9. Neo4j 사용자 그래프 삭제
    sync_user_deletion(user_id)
