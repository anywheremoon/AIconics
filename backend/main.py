from fastapi import FastAPI
import uvicorn

# DB 관련 import
from app.database import Base, engine
from app.models.event_model import Event

# API 라우터
from app.routes import risk_score, events

# ================================
# FastAPI 애플리케이션 생성
# ================================
app = FastAPI(
    title="Risk Scoring API",
    description="User behavior risk scoring server",
    version="1.0.0"
)

# ================================
# DB 테이블 생성
# ================================
# 아직 PostgreSQL을 실행하지 않았으므로 주석 처리
# 3일차 이후 PostgreSQL 연결 후 다시 활성화
#
Base.metadata.create_all(bind=engine)

# ================================
# Router 등록
# ================================
app.include_router(risk_score.router)
app.include_router(events.router)

# ================================
# Health Check
# ================================
@app.get("/")
def health_check():
    return {
        "message": "Risk API server is running"
    }

# ================================
# 프로그램 실행
# ================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )