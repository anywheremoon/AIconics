from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.event_model import Event

# ================================
# API Router 생성
# ================================
router = APIRouter(
    prefix="/api",      # 모든 API 주소 앞에 /api가 붙음
    tags=["Events"],    # Swagger 문서에서 "Events" 그룹으로 표시
    dependencies=[Depends(require_admin)],
)

# ====================================================
# 1. 저장된 행동 로그 전체 조회 API
# ====================================================
@router.get("/events")
def get_events(db: Session = Depends(get_db)):

    # Event 테이블의 모든 데이터를 조회
    events = db.query(Event).all()

    # 조회된 데이터를 JSON 형태로 반환
    return events

# ====================================================
# 2. 위험 사용자의 행동 로그 조회 API
# ====================================================
@router.get("/suspicious-users")
def get_suspicious_users(db: Session = Depends(get_db)):

    # Event 테이블에서 risk_score가 40 이상인 데이터만 조회
    suspicious = (
        db.query(Event)
        .filter(Event.risk_score >= 40)
        .all()
    )

    # 위험 사용자 목록 반환
    return suspicious

# ====================================================
# 특정 행동 로그 삭제 API
# ====================================================
@router.delete("/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
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
