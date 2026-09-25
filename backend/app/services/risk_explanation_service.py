REASON_MESSAGES = {
    "NEW_DEVICE": ("처음 보는 기기에서 접속했습니다.", "IDENTITY"),
    "SHARED_DEVICE": ("여러 사용자가 함께 사용하는 기기입니다.", "IDENTITY"),
    "IP_CHANGED": ("평소와 다른 IP에서 접속했습니다.", "IDENTITY"),
    "LOCATION_CHANGED": ("평소와 다른 위치에서 접속했습니다.", "IDENTITY"),
    "REPEATED_LOGIN": ("짧은 시간 동안 반복 로그인이 감지되었습니다.", "IDENTITY"),
    "ACCOUNT_SWITCHING": ("동일 장치에서 여러 계정 전환이 감지되었습니다.", "IDENTITY"),
    "TYPING_ANOMALY": ("평소와 다른 타이핑 속도가 감지되었습니다.", "BEHAVIOR"),
    "HOLD_TIME_ANOMALY": ("평소와 다른 키 입력 유지 시간이 감지되었습니다.", "BEHAVIOR"),
    "FLIGHT_TIME_ANOMALY": ("평소와 다른 키 입력 간격이 감지되었습니다.", "BEHAVIOR"),
    "MOUSE_CLICK_ANOMALY": ("평소와 다른 마우스 또는 클릭 패턴이 감지되었습니다.", "BEHAVIOR"),
    "ML_ANOMALY": ("One-Class SVM 이상 탐지가 발생했습니다.", "BEHAVIOR"),
}


def build_reasons(
    behavior_reason_codes: list[str],
    identity_reason_codes: list[str],
    contributions: dict[str, int],
) -> list[dict]:
    result = []
    for reason_code in behavior_reason_codes + identity_reason_codes:
        metadata = REASON_MESSAGES.get(reason_code)
        if metadata is None:
            continue
        description, score_type = metadata
        result.append(
            {
                "reason_code": reason_code,
                "description": description,
                "score_type": score_type,
                "score_contribution": contributions.get(reason_code, 0),
            }
        )
    return result
