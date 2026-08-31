from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Event(Base):
    __tablename__ = "behavior_events"

    id = Column(Integer, primary_key=True, index=True)

    # 사용자 / 환경 정보
    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    location = Column(String, nullable=True)

    # 키보드 행동 Feature
    typing_speed = Column(Float, nullable=False)
    avg_hold_time = Column(Float, nullable=False)
    avg_flight_time = Column(Float, nullable=False)
    total_keystrokes = Column(Integer, nullable=False)

    # 마우스 행동 Feature
    mouse_move_count = Column(Integer, nullable=False)
    click_count = Column(Integer, nullable=False)

    # 프로필 비교 결과
    is_new_device = Column(Boolean, nullable=False, default=False)
    profile_deviation_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    # ML 탐지 결과
    detect_anomaly = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # 최종 Risk Score
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )