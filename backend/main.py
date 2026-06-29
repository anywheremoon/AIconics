from fastapi import FastAPI

from app.routes import risk_score, events

app = FastAPI(
    title="Risk Scoring API",
    description="User behavior risk scoring server",
    version="1.0.0"
)

app.include_router(risk_score.router)
app.include_router(events.router)


@app.get("/")
def health_check():
    return {"message": "Risk API server is running"}