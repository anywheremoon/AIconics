from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth_schema import (
    AuthenticatedUserResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services import (
    auth_service,
    device_trust_service,
    session_service,
    user_profile_service,
)
from app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


class SessionLoginRequest(LoginRequest):
    device_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    location: str | None = Field(
        default=None,
        max_length=255,
    )


class SessionTokenResponse(TokenResponse):
    session_id: str
    device_trust_status: str
    baseline_status: str
    login_pattern: dict[str, int | bool]


class SessionLogoutRequest(BaseModel):
    session_id: str = Field(
        min_length=1,
        max_length=36,
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


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
        device_trust_service.record_device_use(
            db,
            user.id,
            data.device_id,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return user


@router.post(
    "/login",
    response_model=SessionTokenResponse,
)
def login(
    data: SessionLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    device_id: str | None = Header(
        default=None,
        alias="X-Device-ID",
    ),
):
    login_result = auth_service.login_user(
        db,
        data,
        device_id or data.device_id,
        _client_ip(request),
    )

    user_id = login_result["user"]["id"]

    resolved_device_id = (
        device_id
        or data.device_id
        or f"unidentified-device-{user_id}"
    )

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

        # 作成したセッションIDをJWTに含める
        access_token = auth_service.create_access_token(
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
        "session_id": user_session.session_id,
        "device_trust_status": trust_status.value,
        "baseline_status": (
            user_profile_service.get_baseline_status(
                db,
                user_id,
            )
        ),
        "login_pattern": pattern,
    }


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
)
def read_current_user(
    current_user=Depends(get_current_user),
):
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
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
        # JWT의 세션과 종료하려는 세션이 일치해야 한다.
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