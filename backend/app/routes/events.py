from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.event_model import Event
from app.schemas.event_schema import EventCreate, EventDetectionResponse
from app.services import session_service, user_profile_service
from app.services.auth_service import get_current_user
from app.services.profile_comparison_service import compare_with_profile
from app.services.risk_engine import calculate_risk_score


router = APIRouter(
    prefix="/api",
    tags=["Events"],
)


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
    user_id = current_user.id
    ip_address = request.client.host if request.client is not None else "unknown"

    user_session = session_service.validate_event_session(
        db,
        event_data.session_id,
        user_id,
        event_data.device_id,
    )

    profile = user_profile_service.get_my_profile(db, user_id)
    baseline_status = user_profile_service.get_baseline_status(db, user_id)

    comparison = compare_with_profile(
        profile,
        event_data,
        current_ip=ip_address,
    )

    risk_result = calculate_risk_score(
        event_data,
        comparison,
        device_trust_status=user_session.device_trust_status,
        repeated_login_detected=user_session.repeated_login_detected,
        account_switch_detected=user_session.account_switch_detected,
        baseline_status=baseline_status,
    )

    db_event = Event(
        user_id=str(user_id),
        session_id=event_data.session_id,
        device_id=event_data.device_id,
        ip_address=ip_address,
        location=event_data.location,
        typing_speed=event_data.typing_speed,
        avg_hold_time=event_data.avg_hold_time,
        avg_flight_time=event_data.avg_flight_time,
        total_keystrokes=event_data.total_keystrokes,
        mouse_move_count=event_data.mouse_move_count,
        click_count=event_data.click_count,
        is_new_device=user_session.device_trust_status == "NEW_DEVICE",
        profile_deviation_score=risk_result["profile_deviation_score"],
        detect_anomaly=risk_result["is_anomaly"],
        behavior_score=risk_result["behavior_score"],
        identity_score=risk_result["identity_score"],
        baseline_status=risk_result["baseline_status"],
        reasons=risk_result["reasons"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
    )

    db.add(db_event)

    user_profile_service.update_behavior_profile(
        db,
        user_id,
        event_data,
    )

    db.commit()
    db.refresh(db_event)

    return EventDetectionResponse(
        event_id=db_event.id,
        risk_score=db_event.risk_score,
        risk_level=db_event.risk_level,
        behavior_score=db_event.behavior_score,
        identity_score=db_event.identity_score,
        baseline_status=db_event.baseline_status,
        reasons=db_event.reasons,
        is_anomaly=db_event.detect_anomaly,
        profile_deviation_score=db_event.profile_deviation_score,
    )


@router.get("/events")
def get_events(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return db.query(Event).all()


@router.get("/suspicious-users")
def get_suspicious_users(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return db.query(Event).filter(Event.risk_score >= 40).all()


@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()

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
