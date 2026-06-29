from fastapi import APIRouter

router = APIRouter(
    prefix="/api",
    tags=["Events"]
)


@router.get("/events")
def get_events():
    return {"message": "events api"}


@router.get("/suspicious-users")
def get_suspicious_users():
    return {"message": "suspicious users api"}