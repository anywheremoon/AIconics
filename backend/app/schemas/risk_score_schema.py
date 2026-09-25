from datetime import datetime

from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_level: str
    message: str


class UserRiskScoreResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_level: str
    is_anomaly: bool
    profile_deviation_score: float
    created_at: datetime


class SuspiciousUserResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_level: str
    is_anomaly: bool
    profile_deviation_score: float
    created_at: datetime