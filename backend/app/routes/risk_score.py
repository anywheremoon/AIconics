from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.event_schema import EventCreate
from app.schemas.risk_score_schema import RiskScoreResponse

from app.models.event_model import Event
from app.database import get_db

from app.services.risk_engine import calculate_risk_score
from app.services.auth_service import get_current_user


# ================================
# API Router 생성
# ================================
router = APIRouter(
    prefix="/api",
    tags=["Risk Score"],
    dependencies=[Depends(get_current_user)],
)


# POST /api/risk-score 요청 처리
@router.post("/risk-score", response_model=RiskScoreResponse)
def create_risk_score(
    event_data: EventCreate,
    db: Session = Depends(get_db)
):

    # ====================================================
    # 1. 규칙 기반 점수 + ML 이상 탐지 결과 계산
    # ====================================================

    result = calculate_risk_score(event_data)

    score = result["risk_score"]
    level = result["risk_level"]

    is_anomaly = result["is_anomaly"]
    ml_prediction = result["ml_prediction"]
    ml_decision_score = result["ml_decision_score"]


    # ====================================================
    # 2. DB에 저장할 Event 객체 생성
    # ====================================================

    db_event = Event(
        user_id=event_data.user_id,
        device_id=event_data.device_id,
        ip_address=event_data.ip_address,
        location=event_data.location,
        typing_speed=event_data.typing_speed,
        mouse_move_count=event_data.mouse_move_count,
        click_count=event_data.click_count,
        is_new_device=event_data.is_new_device,

        risk_score=score,
        risk_level=level
    )


    # ====================================================
    # 3. 데이터베이스에 저장
    # ====================================================

    db.add(db_event)
    db.commit()
    db.refresh(db_event)


    # ====================================================
    # 4. 클라이언트에게 결과 반환
    # ====================================================

    return RiskScoreResponse(
        user_id=db_event.user_id,
        risk_score=db_event.risk_score,
        risk_level=db_event.risk_level,
        message=(
            f"Risk analysis complete. "
            f"Level: {level}, "
            f"Anomaly: {is_anomaly}, "
            f"ML prediction: {ml_prediction}, "
            f"Decision score: {ml_decision_score:.4f}"
        )
    )
