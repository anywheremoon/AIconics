import requests
import config


def send_event(
    event,
    *,
    access_token,
    session_id,
    auth_version,
):
    """수집 시작 시점의 인증정보로 행동 이벤트를 전송한다."""

    if not config.auth_is_current(
        access_token, session_id, auth_version
    ):
        print("인증정보가 변경되어 이전 수집 데이터 전송을 취소합니다.")
        return False

    if str(event.get("session_id", "")) != str(session_id):
        print("이벤트와 수집 세션이 달라 전송을 취소합니다.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            config.API_URL,
            json=event,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )

        print("Status Code :", response.status_code)

        try:
            print("Response :", response.json())
        except ValueError:
            print("Response :", response.text)

        if response.status_code == 401:
            config.clear_agent_auth_if_current(
                access_token,
                session_id,
                auth_version,
            )
            print("인증이 만료되었거나 세션이 종료되었습니다.")
            print("웹에서 Agent 인증을 다시 연결해야 합니다.")
            return False

        if response.status_code == 403:
            print("이벤트 전송 권한이 없습니다.")
            return False

        if response.status_code == 409:
            print("이벤트가 충돌로 거부되었습니다. 응답 내용을 확인하세요.")
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
        print("API 전송 실패:", error)
        return False