import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.login_history_model import LoginHistory
from app.repositories import user_repository
from app.services import user_profile_service


PASSWORD_ITERATIONS = 600_000
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(48)
    warnings.warn(
        "JWT_SECRET_KEY is not set; tokens will be invalid after the process restarts.",
        RuntimeWarning,
        stacklevel=2,
    )

bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256" or int(iterations) != PASSWORD_ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), _b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(_b64decode(expected), actual)
    except (ValueError, TypeError, binascii.Error):
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def verify_access_token(token: str) -> int:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_b64decode(encoded_header))
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported JWT header")
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(encoded_signature)):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64decode(encoded_payload))
        if int(payload["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Expired token")
        return int(payload["sub"])
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise credentials_error


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_repository.find_by_id(db, verify_access_token(credentials.credentials))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def create_virtual_account(db: Session, user_id: int):
    """Integration point owned by B; no-op until B's service is merged."""
    try:
        from app.services.account_service import create_virtual_account as account_creator
    except ModuleNotFoundError as error:
        if error.name == "app.services.account_service":
            return None
        raise
    return account_creator(db, user_id)


def register_user(db: Session, data, ip_address: str | None = None):
    if user_repository.username_exists(db, data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    try:
        user = user_repository.create_user(db, data.username, hash_password(data.password))
        create_virtual_account(db, user.id)
        user_profile_service.create_initial_profile(
            db, user.id, data.device_id, ip_address, data.location
        )
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from error
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
    user = user_repository.find_by_username(db, data.username)
    if user is None or not verify_password(data.password, user.password_hash):
        _save_login_history(db, user.id if user else None, device_id, ip_address, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id)
    _save_login_history(db, user.id, device_id, ip_address, True)
    return {"access_token": token, "token_type": "bearer"}
