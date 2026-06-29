from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_level: str
    message: str