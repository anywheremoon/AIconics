import requests
import config


def send_event(event):
    """
    FastAPI 서버로 행동 이벤트 전송
    """

    if not config.ACCESS_TOKEN:
        print("Agent 인증정보가 없습니다.")
        print("사용자 로그인 후 Agent 인증 연결이 필요합니다.")
        return False

    token = config.ACCESS_TOKEN.strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            config.API_URL,
            json=event,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )

        print(
            f"Status Code : {response.status_code}"
        )

        try:
            print(
                "Response :",
                response.json()
            )
        except ValueError:
            print(
                "Response :",
                response.text
            )

        if response.status_code == 401:
            print(
                "Agent 인증에 실패했습니다."
            )
            print(
                "JWT가 만료되었거나 유효하지 않습니다."
            )
            return False

        if response.status_code == 403:
            print(
                "Agent에 이벤트 전송 권한이 없습니다."
            )
            return False

        if response.status_code == 409:
            print(
                "로그인 세션의 기기와 "
                "현재 Agent 기기가 일치하지 않습니다."
            )
            return False

        response.raise_for_status()

        print("서버 전송 완료")
        return True

    except requests.exceptions.Timeout:
        print(
            "API 요청 시간이 초과되었습니다."
        )
        return False

    except requests.exceptions.ConnectionError:
        print(
            "FastAPI 서버에 연결할 수 없습니다."
        )
        return False

    except requests.exceptions.RequestException as e:
        print(
            "API 전송 실패"
        )
        print(e)
        return False