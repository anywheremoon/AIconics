from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    __table_args__ = (
        UniqueConstraint(
            "risk_assessment_id",
            "score_type",
            "reason_code",
            name="uq_risk_factor_assessment_type_reason",
        ),
        CheckConstraint(
            "score_contribution >= 0",
            name="ck_risk_factors_score_contribution",
        ),
        CheckConstraint(
            "final_score_contribution IS NULL OR "
            "final_score_contribution >= 0",
            name="ck_risk_factors_final_contribution",
        ),
        CheckConstraint(
            "score_type IN ("
            "'BEHAVIOR', 'IDENTITY', 'TRANSACTION', 'GRAPH'"
            ")",
            name="ck_risk_factors_score_type",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    risk_assessment_id = Column(
        Integer,
        ForeignKey(
            "risk_assessments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    reason_code = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        String(500),
        nullable=False,
    )

    score_type = Column(
        String(20),
        nullable=False,
    )

    # 해당 엔진 내부의 원점수 기여도
    # 예: Behavior의 ML_ANOMALY +20
    score_contribution = Column(
        Float,
        nullable=False,
    )

    # 환산 및 가중치 적용 후 최종 점수에 기여한 값
    # 정확한 배분이 정해지지 않은 경우 None
    final_score_contribution = Column(
        Float,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )