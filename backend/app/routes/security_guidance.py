from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.security_guidance_schema import SecurityGuidanceResponse
from app.services import additional_auth_service, auth_service
from app.services.security_guidance_service import generate_security_guidance


router = APIRouter(
    prefix="/api/auth",
    tags=["Security Guidance"],
)


class SecurityGuidanceRequest(BaseModel):
    session_id: str


@router.post(
    "/guidance",
    response_model=SecurityGuidanceResponse,
)
def get_security_guidance(
    data: SecurityGuidanceRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        auth_service.bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verification token required",
        )

    user_session = additional_auth_service.get_limited_session(
        db,
        credentials.credentials,
        data.session_id,
        allow_pending=True,
    )

    return generate_security_guidance(
        login_status=user_session.auth_status,
        reason_codes=user_session.auth_reason_codes or [],
    )