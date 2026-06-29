from fastapi import APIRouter

router = APIRouter(
    prefix="/api",
    tags=["Risk Score"]
)


@router.post("/risk-score")
def create_risk_score():
    return {"message": "risk score api"}