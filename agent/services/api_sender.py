import requests

import config


def send_event(
    event,
    *,
    access_token,
    session_id,
    stop_event,
):
    """수집 당시 인증정보로 행동 이벤트를 전송한다."""

    if not config.is_auth_current(
        access_token,
        session_id,
        stop_event,
    ):
        print("인증 상태 변경 - 이벤트 전송을 취소합니다.")
        return False

    if event.get("session_id") != session_id:
        print("수집 세션과 이벤트 세션이 달라 전송을 취소합니다.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json",
    }

    try:
        # 요청 직전 한 번 더 확인
        if not config.is_auth_current(
            access_token,
            session_id,
            stop_event,
        ):
            print("로그아웃 또는 세션 변경 - 전송을 취소합니다.")
            return False

        response = requests.post(
            config.API_URL,
            json=event,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )

        print(f"Status Code : {response.status_code}")

        if response.status_code == 401:
            print("인증 실패: JWT가 만료되었거나 유효하지 않습니다.")
            return False

        if response.status_code == 403:
            print("Agent에 이벤트 전송 권한이 없습니다.")
            return False

        if response.status_code == 409:
            print("세션 또는 기기 정보 충돌입니다.")
            return False

        response.raise_for_status()
        return True

    except requests.exceptions.Timeout:
        print("API 요청 시간이 초과되었습니다.")
        return False

    except requests.exceptions.ConnectionError:
        print("FastAPI 서버에 연결할 수 없습니다.")
        return False

    except requests.exceptions.RequestException as error:
        print(f"API 전송 실패: {error}")
        return False