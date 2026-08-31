from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.dependencies.auth_dependency import require_admin

from app.database import get_db
from app.models.event_model import Event
from app.schemas.event_schema import (
    EventCreate,
    EventDetectionResponse,
)

from app.services.auth_service import get_current_user
from app.services.profile_comparison_service import compare_with_profile
from app.services.risk_engine import calculate_risk_score
from app.services import user_profile_service


router = APIRouter(
    prefix="/api",
    tags=["Events"],
)


# ==========================================
# 행동 이벤트 수집 + 위험도 분석
# ==========================================
@router.post(
    "/events",
    response_model=EventDetectionResponse,
)
def create_event(
    event_data: EventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # ------------------------------------------
    # 1. JWT에서 인증된 사용자 확인
    # ------------------------------------------
    user_id = current_user.id

    # 클라이언트가 직접 보내는 값이 아니라
    # 실제 요청에서 IP 주소 추출
    ip_address = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    # ------------------------------------------
    # 2. 현재 사용자 Profile 조회
    # ------------------------------------------
    profile = user_profile_service.get_my_profile(
        db,
        user_id,
    )

    # ------------------------------------------
    # 3. 현재 행동과 기존 Profile 비교
    # ------------------------------------------
    comparison = compare_with_profile(
        profile,
        event_data,
    )

    # ------------------------------------------
    # 4. Profile 비교 + ML Risk Score 계산
    # ------------------------------------------
    risk_result = calculate_risk_score(
        event_data,
        comparison,
    )

    # ------------------------------------------
    # 5. Event DB 저장
    # ------------------------------------------
    db_event = Event(
        user_id=str(user_id),
        device_id=event_data.device_id,
        ip_address=ip_address,
        location=event_data.location,

        typing_speed=event_data.typing_speed,
        avg_hold_time=event_data.avg_hold_time,
        avg_flight_time=event_data.avg_flight_time,
        total_keystrokes=event_data.total_keystrokes,

        mouse_move_count=event_data.mouse_move_count,
        click_count=event_data.click_count,

        is_new_device=comparison["new_device"],
        profile_deviation_score=comparison[
            "profile_deviation_score"
        ],

        detect_anomaly=risk_result["is_anomaly"],

        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # ------------------------------------------
    # 6. 현재는 기존 Profile event_count 갱신
    # ------------------------------------------
    user_profile_service.update_profile_event_count(
        db,
        user_id,
    )

    # ------------------------------------------
    # 7. 결과 반환
    # ------------------------------------------
    return EventDetectionResponse(
        event_id=db_event.id,
        risk_score=db_event.risk_score,
        risk_level=db_event.risk_level,
        is_anomaly=db_event.detect_anomaly,
        profile_deviation_score=(
            db_event.profile_deviation_score
        ),
    )


# ==========================================
# 기존 Event 전체 조회
# ==========================================
@router.get("/events")
def get_events(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return db.query(Event).all()

# ==========================================
# 기존 Suspicious User 조회
# ==========================================
@router.get("/suspicious-users")
def get_suspicious_users(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return (
        db.query(Event)
        .filter(Event.risk_score >= 40)
        .all()
    )


# ==========================================
# 기존 Event 삭제
# ==========================================
@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="해당 행동 로그를 찾을 수 없습니다.",
        )

    db.delete(event)
    db.commit()

    return {
        "message": "행동 로그가 삭제되었습니다.",
        "event_id": event_id,
    }