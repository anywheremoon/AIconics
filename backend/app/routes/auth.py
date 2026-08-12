from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth_schema import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services import auth_service


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    return auth_service.register_user(db, data, _client_ip(request))


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    device_id: str | None = Header(default=None, alias="X-Device-ID"),
):
    return auth_service.login_user(db, data, device_id, _client_ip(request))
