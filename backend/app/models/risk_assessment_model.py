from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.sql import func

from app.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    __table_args__ = (
        CheckConstraint(
            "behavior_score >= 0 AND behavior_score <= 100",
            name="ck_risk_assessments_behavior_score",
        ),
        CheckConstraint(
            "identity_score >= 0 AND identity_score <= 100",
            name="ck_risk_assessments_identity_score",
        ),
        CheckConstraint(
            "transaction_score >= 0 AND transaction_score <= 100",
            name="ck_risk_assessments_transaction_score",
        ),
        CheckConstraint(
            "graph_score IS NULL OR "
            "(graph_score >= 0 AND graph_score <= 100)",
            name="ck_risk_assessments_graph_score",
        ),
        CheckConstraint(
            "final_risk_score >= 0 AND final_risk_score <= 100",
            name="ck_risk_assessments_final_score",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_risk_assessments_level",
        ),
        CheckConstraint(
            "decision IN ("
            "'APPROVED', "
            "'REQUIRE_VERIFICATION', "
            "'PENDING_REVIEW', "
            "'ACCOUNT_REVIEW'"
            ")",
            name="ck_risk_assessments_decision",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    transaction_id = Column(
        Integer,
        ForeignKey(
            "transactions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # 각 엔진에서 받은 원점수
    behavior_score = Column(Float, nullable=False)
    identity_score = Column(Float, nullable=False)
    transaction_score = Column(Float, nullable=False)

    # Graph 분석을 받지 못한 경우 None.
    # 미분석 상태를 0점으로 표현하지 않는다.
    graph_score = Column(Float, nullable=True)

    final_risk_score = Column(Float, nullable=False)

    risk_level = Column(
        String(20),
        nullable=False,
    )

    decision = Column(
        String(32),
        nullable=False,
    )

    # 예: weighted_rules_v1
    # 정책 변경 전후의 평가를 구분하기 위한 값
    policy_version = Column(
        String(50),
        nullable=False,
    )

    # 당시 가중치, 환산 최대값, 환산 점수,
    # 각 영역의 최종 점수 기여도 등을 저장
    calculation_details = Column(
        JSON,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )