from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

RiskDecision = Literal[
    "APPROVED",
    "REQUIRE_VERIFICATION",
    "PENDING_REVIEW",
    "ACCOUNT_REVIEW",
]

ScoreType = Literal[
    "BEHAVIOR",
    "IDENTITY",
    "TRANSACTION",
    "GRAPH",
]


class FinalRiskReason(BaseModel):
    reason_code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    score_type: ScoreType
    score_contribution: float = Field(ge=0, le=100)


class WeightedContributions(BaseModel):
    behavior: float = Field(ge=0, le=100)
    identity: float = Field(ge=0, le=100)
    transaction: float = Field(ge=0, le=100)


class FinalRiskResult(BaseModel):
    # 각 엔진에서 받은 원점수
    behavior_score: float = Field(ge=0, le=100)
    identity_score: float = Field(ge=0, le=100)
    transaction_score: float = Field(ge=0, le=100)
    graph_score: float | None = Field(default=None, ge=0, le=100)

    # 현재 score_combiner.py가 계산한 환산 점수
    normalized_behavior_score: float = Field(ge=0, le=100)
    normalized_identity_score: float = Field(ge=0, le=100)
    weighted_contributions: WeightedContributions

    final_risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    decision: RiskDecision

    reasons: list[FinalRiskReason] = Field(default_factory=list)