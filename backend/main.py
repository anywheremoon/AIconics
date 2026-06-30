from fastapi import FastAPI
import uvicorn

# ================================
# 필요한 모듈 import
# ================================

# app/routes 폴더에 있는 API 라우터 가져오기
from app.routes import risk_score, events


# ================================
# FastAPI 애플리케이션 생성
# ================================

# FastAPI 서버 객체 생성
app = FastAPI(
    title="Risk Scoring API",                  # Swagger 문서 제목
    description="User behavior risk scoring server",   # API 설명
    version="1.0.0"                            # API 버전
)


# ================================
# 라우터(Router) 등록
# ================================

# risk_score.py에 정의된 API 등록
app.include_router(risk_score.router)

# events.py에 정의된 API 등록
app.include_router(events.router)


# ================================
# 서버 상태 확인(Health Check) API
# ================================

# GET /
@app.get("/")
def health_check():
    return {
        "message": "Risk API server is running"
    }


# ================================
# 프로그램 실행
# ================================

# 이 파일을 직접 실행했을 때만 서버 실행
if __name__ == "__main__":

    # Uvicorn 서버 실행
    uvicorn.run(
        "main:app",        # main.py 안의 app 객체 실행
        host="127.0.0.1",  # localhost에서만 접속 가능
        port=8000,         # 8000번 포트 사용
        reload=True        # 코드 수정 시 서버 자동 재시작(개발용)
    )