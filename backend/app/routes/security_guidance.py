from fastapi import APIRouter, HTTPException, status

from app.schemas.security_guidance_schema import SecurityGuidanceResponse


router = APIRouter(
    prefix="/api/auth",
    tags=["Security Guidance"],
)


@router.post(
    "/guidance",
    response_model=SecurityGuidanceResponse,
)
def get_security_guidance():
    # TODO: A의 제한 토큰 검증 및 세션 조회 기능 연결
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Security guidance authentication is not configured yet",
    )