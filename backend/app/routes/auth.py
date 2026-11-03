from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import user_repository
from app.schemas.auth_schema import (
    AuthenticatedUserResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerificationConfirmRequest,
    VerificationConfirmResponse,
    VerificationIssueResponse,
    VerificationRequest,
)
from app.services import (
    additional_auth_service,
    auth_service,
    device_trust_service,
    session_service,
    user_profile_service,
)
from app.services.auth_service import get_current_user


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class SessionLogoutRequest(BaseModel):
    session_id: str = Field(
        min_length=1,
        max_length=36,
    )

class SessionLoginRequest(LoginRequest):
    device_id: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class SessionTokenResponse(TokenResponse):
    session_id: str
    login_status: Literal[
        "AUTHENTICATED",
        "REQUIRE_VERIFICATION",
        "PENDING_REVIEW",
    ]
    requires_verification: bool
    reason_codes: list[str]
    verification_token: str | None = None
    device_trust_status: str
    baseline_status: str
    login_pattern: dict[str, int | bool]


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _limited_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verification authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth_service.register_user(
        db,
        data,
        _client_ip(request),
    )
    try:
        device_trust_service.record_device_use(db, user.id, data.device_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return user


@router.post("/login", response_model=SessionTokenResponse)
def login(
    data: SessionLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    device_id: str | None = Header(
        default=None,
        alias="X-Device-ID",
        min_length=1,
        max_length=255,
    ),
):
    resolved_device_id = device_id or data.device_id
    if resolved_device_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A device ID is required for login",
        )

    login_result = auth_service.login_user(
        db,
        data,
        resolved_device_id,
        _client_ip(request),
    )
    user_id = login_result["user"]["id"]
    try:
        user_session, trust_status, pattern = (
            session_service.create_login_session(
                db,
                user_id,
                resolved_device_id,
                _client_ip(request),
                data.location,
            )
        )

        # 기기 신뢰 상태와 로그인 패턴을 바탕으로 인증 상태를 결정한다.
        login_status, reason_codes = auth_service.determine_login_state(
            trust_status,
            pattern,
            user_role=login_result["user"]["role"],
        )
        user_session.auth_status = login_status
        user_session.auth_reason_codes = reason_codes

        access_token = None
        verification_token = None
        if login_status == "AUTHENTICATED":
            access_token = auth_service.create_access_token(
                user_id,
                user_session.session_id,
            )
        else:
            verification_token = auth_service.create_verification_token(
                user_id,
                user_session.session_id,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        **login_result,
        "access_token": access_token,
        "login_status": login_status,
        "requires_verification": login_status == "REQUIRE_VERIFICATION",
        "reason_codes": reason_codes,
        "session_id": user_session.session_id,
        "verification_token": verification_token,
        "device_trust_status": trust_status.value,
        "baseline_status": user_profile_service.get_baseline_status(db, user_id),
        "login_pattern": pattern,
    }


@router.post(
    "/verification/request",
    response_model=VerificationIssueResponse,
)
def request_verification(
    data: VerificationRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        auth_service.bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    try:
        user_session = additional_auth_service.get_limited_session(
            db,
            _limited_token(credentials),
            data.session_id,
        )
        code, expires_in = additional_auth_service.issue_code(
            db, user_session
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "session_id": user_session.session_id,
        "expires_in_seconds": expires_in,
        "retry_after_seconds": (
            additional_auth_service.VERIFICATION_REQUEST_COOLDOWN_SECONDS
        ),
        "verification_code": (
            code
            if additional_auth_service.expose_code_in_response()
            else None
        ),
    }


@router.post(
    "/verification/confirm",
    response_model=VerificationConfirmResponse,
)
def confirm_verification(
    data: VerificationConfirmRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        auth_service.bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    try:
        user_session = additional_auth_service.get_limited_session(
            db,
            _limited_token(credentials),
            data.session_id,
        )
        access_token = additional_auth_service.confirm_code(
            db, user_session, data.code
        )
        user = user_repository.find_by_id(db, user_session.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user no longer exists",
            )
        db.commit()
    except HTTPException as error:
        # Keep the failed-attempt counter and possible PENDING transition.
        if error.status_code == status.HTTP_400_BAD_REQUEST:
            db.commit()
        else:
            db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "login_status": "AUTHENTICATED",
        "requires_verification": False,
        "reason_codes": [],
        "session_id": user_session.session_id,
        "verification_token": None,
    }


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
)
def read_current_user(
    current_user=Depends(get_current_user),
):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service.delete_user_account(
        db,
        current_user,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    data: SessionLogoutRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # JWT의 세션 ID와 종료하려는 세션 ID가 일치하는지 확인한다.
        auth_service.require_matching_token_session(
            request,
            data.session_id,
        )

        session_service.end_login_session(
            db,
            session_id=data.session_id,
            user_id=current_user.id,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise