from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# ================================
# 필요한 모듈 import
# ================================

# 요청(Request)과 응답(Response)에 사용할 Pydantic 스키마
from app.schemas import EventCreate, RiskScoreResponse

# DB에 저장할 SQLAlchemy 모델
from app.models import Event

# 데이터베이스 세션을 가져오는 함수
from app.database import get_db

# 위험 점수 계산 함수와 위험 등급 판별 함수
from app.services import calculate_risk_score, get_risk_level


# ================================
# API Router 생성
# ================================
router = APIRouter(
    prefix="/api",          # 모든 API 주소 앞에 /api가 붙음
    tags=["Risk Score"]     # Swagger 문서에서 "Risk Score" 그룹으로 표시
)


# POST /api/risk-score 요청 처리
@router.post("/risk-score", response_model=RiskScoreResponse)
def create_risk_score(
    event_data: EventCreate,             # 클라이언트가 보낸 JSON 데이터
    db: Session = Depends(get_db)        # DB 연결(Session) 자동 생성
):
    
    # ====================================================
    # 1. 위험 점수 계산
    # ====================================================
    
    # event_data(Pydantic 객체)를 dict 형태로 변환해서 위험 점수 계산 함수에 전달
    score = calculate_risk_score(event_data.dict())

    # 계산된 점수를 바탕으로 위험 등급 결정
    level = get_risk_level(score)


    # ====================================================
    # 2. DB에 저장할 Event 객체 생성
    # ====================================================
    
    # 사용자가 보낸 데이터 + 계산된 위험 점수를 하나의 객체로 생성
    db_event = Event(
        user_id=event_data.user_id,
        device_id=event_data.device_id,
        ip_address=event_data.ip_address,
        location=event_data.location,
        typing_speed=event_data.typing_speed,
        mouse_move_count=event_data.mouse_move_count,
        click_count=event_data.click_count,
        is_new_device=event_data.is_new_device,

        # 계산된 결과 저장
        risk_score=score,
        risk_level=level
    )


    # ====================================================
    # 3. 데이터베이스에 저장
    # ====================================================

    # Session에 저장할 객체 추가
    db.add(db_event)

    # 실제 DB에 INSERT 실행
    db.commit()

    # DB에서 최신 정보를 다시 가져옴
    db.refresh(db_event)


    # ====================================================
    # 4. 클라이언트에게 결과 반환
    # ====================================================

    # response_model(RiskScoreResponse) 형식에 맞춰 응답 생성
    return RiskScoreResponse(
        user_id=db_event.user_id,              # 사용자 ID
        risk_score=db_event.risk_score,        # 계산된 위험 점수
        risk_level=db_event.risk_level,        # 위험 등급
        message=f"Risk analysis complete. Level: {level}"
    )