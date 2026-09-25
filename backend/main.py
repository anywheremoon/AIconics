import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette import status

from app.database import Base, engine
from app.models.event_model import Event
from app.routes import (
    accounts,
    auth,
    dashboard,
    events,
    risk_score,
    transaction_risk,
    transactions,
    user_profiles,
)


app = FastAPI(
    title="Risk Scoring API",
    description="User behavior risk scoring server",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logger = logging.getLogger(__name__)


@app.on_event("startup")
def initialize_database():
    """Create database tables when PostgreSQL is available."""
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as error:
        logger.warning(
            "Database is unavailable; tables were not initialized: %s",
            error,
        )


app.include_router(auth.router)
app.include_router(user_profiles.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(risk_score.router)
app.include_router(transaction_risk.router)
app.include_router(events.router)
app.include_router(dashboard.router)


@app.get("/")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "PostgreSQL is unavailable. "
                "Start the database and verify DATABASE_URL."
            ),
        ) from error

    return {
        "message": "Risk API server is running",
        "database": "connected",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
