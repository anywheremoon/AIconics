REASON_MESSAGES = {
    "NEW_DEVICE": {
        "description": "처음 보는 기기에서 접속했습니다.",
        "score_type": "IDENTITY",
    },
    "SHARED_DEVICE": {
        "description": "여러 사용자가 함께 사용하는 기기입니다.",
        "score_type": "IDENTITY",
    },
    "IP_CHANGED": {
        "description": "평소와 다른 IP에서 접속했습니다.",
        "score_type": "IDENTITY",
    },
    "LOCATION_CHANGED": {
        "description": "평소와 다른 위치에서 접속했습니다.",
        "score_type": "IDENTITY",
    },
    "REPEATED_LOGIN": {
        "description": "짧은 시간 동안 반복 로그인이 감지되었습니다.",
        "score_type": "IDENTITY",
    },
    "ACCOUNT_SWITCHING": {
        "description": "동일 장치에서 여러 계정 전환이 감지되었습니다.",
        "score_type": "IDENTITY",
    },
    "TYPING_ANOMALY": {
        "description": "평소와 다른 타이핑 속도가 감지되었습니다.",
        "score_type": "BEHAVIOR",
    },
    "HOLD_TIME_ANOMALY": {
        "description": "평소와 다른 키 입력 유지 시간이 감지되었습니다.",
        "score_type": "BEHAVIOR",
    },
    "FLIGHT_TIME_ANOMALY": {
        "description": "평소와 다른 키 입력 간격이 감지되었습니다.",
        "score_type": "BEHAVIOR",
    },
    "MOUSE_CLICK_ANOMALY": {
        "description": "평소와 다른 마우스 또는 클릭 패턴이 감지되었습니다.",
        "score_type": "BEHAVIOR",
    },
    "ML_ANOMALY": {
        "description": "One-Class SVM 이상 탐지가 발생했습니다.",
        "score_type": "BEHAVIOR",
    },
}


def build_reasons(
    behavior_reason_codes: list[str],
    identity_reason_codes: list[str],
    contributions: dict[str, int],
) -> list[dict]:
    """
    reason_code 목록을 관리자 화면/API에서 사용할 수 있는
    구조화된 판단 근거 목록으로 변환한다.
    """

    result = []

    for reason_code in behavior_reason_codes + identity_reason_codes:
        metadata = REASON_MESSAGES.get(reason_code)

        if metadata is None:
            continue

        result.append(
            {
                "reason_code": reason_code,
                "description": metadata["description"],
                "score_type": metadata["score_type"],
                "score_contribution": contributions.get(
                    reason_code,
                    0,
                ),
            }
        )

    return result