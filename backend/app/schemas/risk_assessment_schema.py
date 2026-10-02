from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RiskFactorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason_code: str
    description: str
    score_type: str
    score_contribution: float
    final_score_contribution: float | None


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int

    behavior_score: float
    identity_score: float
    transaction_score: float
    graph_score: float | None
    final_risk_score: float

    risk_level: str
    decision: str
    policy_version: str
    calculation_details: dict[str, Any]
    created_at: datetime

    factors: list[RiskFactorResponse]