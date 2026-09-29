from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_model import Event


def get_latest_behavior_identity(
    db: Session,
    *,
    user_id: int,
    session_id: str,
) -> dict:
    """
    거래를 요청한 사용자의 현재 세션에서 발생한
    가장 최근 행동 이벤트의 점수와 판단 근거를 가져온다.

    session_id는 클라이언트가 임의로 지정한 값을 그대로
    신뢰하지 말고, 인증된 활성 세션을 확인한 뒤 전달해야 한다.
    """
    if not session_id:
        raise ValueError("활성 세션 ID가 필요합니다.")

    event = (
        db.query(Event)
        .filter(
            Event.user_id == str(user_id),
            Event.session_id == session_id,
        )
        .order_by(Event.created_at.desc(), Event.id.desc())
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="현재 세션의 행동 데이터가 없어 거래 위험을 평가할 수 없습니다.",
        )

    reasons = event.reasons or []

    if not isinstance(reasons, list):
        raise ValueError("저장된 행동 위험 사유 형식이 올바르지 않습니다.")

    return {
        "behavior_score": event.behavior_score,
        "identity_score": event.identity_score,
        "behavior_reasons": [
            reason
            for reason in reasons
            if isinstance(reason, dict)
            and reason.get("score_type") == "BEHAVIOR"
        ],
        "identity_reasons": [
            reason
            for reason in reasons
            if isinstance(reason, dict)
            and reason.get("score_type") == "IDENTITY"
        ],
        "event_id": event.id,
    }