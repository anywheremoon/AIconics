from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

# ================================
# 필요한 모듈 import
# ================================

# Event 테이블(SQLAlchemy 모델)
from app.models import Event

# 데이터베이스 연결(Session)을 생성하는 함수
from app.database import get_db


# ================================
# API Router 생성
# ================================
router = APIRouter(
    prefix="/api",      # 모든 API 주소 앞에 /api가 붙음
    tags=["Events"]     # Swagger 문서에서 "Events" 그룹으로 표시
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