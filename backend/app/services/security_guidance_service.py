from app.services.llm_service import (
    LLMServiceError,
    generate_llm_response,
)


LOGIN_STATUSES = {
    "AUTHENTICATED",
    "REQUIRE_VERIFICATION",
    "PENDING",
}


DEFAULT_GUIDANCE = {
    "AUTHENTICATED": {
        "summary": "로그인이 정상적으로 완료되었습니다.",
        "next_action": "서비스를 이용하실 수 있습니다.",
    },
    "REQUIRE_VERIFICATION": {
        "summary": "로그인 시 추가 인증이 필요합니다.",
        "next_action": "화면의 안내에 따라 추가 인증을 진행해 주세요.",
    },
    "PENDING": {
        "summary": "보안상의 이유로 로그인이 보류되었습니다.",
        "next_action": "잠시 후 다시 시도하거나 관리자에게 문의해 주세요.",
    },
}


REASON_DESCRIPTIONS = {
    "NEW_DEVICE": "평소 사용하지 않던 새로운 기기에서 로그인했습니다.",
    "UNUSUAL_BEHAVIOR": "평소와 다른 로그인 행동이 감지되었습니다.",
    "HIGH_RISK": "로그인 과정에서 높은 보안 위험이 감지되었습니다.",
}


def get_default_guidance(
    login_status: str,
    reason_codes: list[str],
    is_admin: bool = False,
) -> dict:
    guidance = DEFAULT_GUIDANCE.get(
        login_status,
        {
            "summary": "로그인 상태를 확인하고 있습니다.",
            "next_action": "잠시 후 다시 시도해 주세요.",
        },
    ).copy()

    if is_admin:
        reasons = [
            REASON_DESCRIPTIONS.get(code, code)
            for code in reason_codes
        ]

        guidance["summary"] = (
            f"로그인 상태: {login_status}. "
            + " ".join(reasons)
        )

        guidance["next_action"] = (
            "로그인 위험 상태와 추가 인증 진행 여부를 확인하세요."
        )

    return guidance


def generate_security_guidance(
    login_status: str,
    reason_codes: list[str],
    is_admin: bool = False,
) -> dict:
    default = get_default_guidance(
        login_status,
        reason_codes,
        is_admin,
    )

    audience = "보안 관리자" if is_admin else "일반 사용자"

    reasons = [
        REASON_DESCRIPTIONS.get(
            code,
            "보안 확인이 필요합니다.",
        )
        for code in reason_codes
    ]

    prompt = f"""
다음은 금융 서비스의 로그인 보안 분석 결과입니다.

대상: {audience}
로그인 상태: {login_status}
사유: {", ".join(reasons) if reasons else "별도 위험 사유 없음"}

기존에 결정된 로그인 상태를 변경하지 마세요.
비밀번호나 인증번호 입력을 요청하지 마세요.
위험 점수나 내부 보안 규칙을 추측하지 마세요.

다음 형식으로 한국어 안내를 작성하세요.

요약: 한 문장
다음 행동: 한 문장
"""

    try:
        response = generate_llm_response(prompt)

        summary = ""
        next_action = ""

        for line in response.splitlines():
            line = line.strip()

            if line.startswith("요약:"):
                summary = line.split(":", 1)[1].strip()

            elif line.startswith("다음 행동:"):
                next_action = line.split(":", 1)[1].strip()

        if not summary or not next_action:
            return default

        return {
            "summary": summary,
            "next_action": next_action,
        }

    except LLMServiceError:
        return default