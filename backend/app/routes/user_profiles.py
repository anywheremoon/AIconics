from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.schemas.user_profile_schema import UserProfileResponse
from app.services.auth_service import get_current_user
from app.services.user_profile_service import get_user_baseline


router = APIRouter(prefix="/api/user-profiles", tags=["User Profiles"])


@router.get("/me", response_model=UserProfileResponse)
def read_my_profile(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_user_baseline(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return profile


@router.get("/{user_id}", response_model=UserProfileResponse)
def read_user_profile(
    user_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    profile = get_user_baseline(db, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    return profile
