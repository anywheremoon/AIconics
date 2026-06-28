#0단계 작업, 1~2일차 작업 최소 코드
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check():
    return {"message": "Risk API server is running"}