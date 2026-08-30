import requests
import config


def send_event(event):
    """
    FastAPI 서버로 이벤트 전송
    """

    # JWT 토큰이 없으면 전송하지 않음
    if not config.ACCESS_TOKEN:
        print("AGENT_ACCESS_TOKEN이 설정되지 않았습니다.")
        return False

    headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}"
    }

    try:
        response = requests.post(
            config.API_URL,
            json=event,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT
        )

        print(f"Status Code : {response.status_code}")

        try:
            print("Response :", response.json())
        except Exception:
            print("Response :", response.text)

        response.raise_for_status()

        return True

    except requests.exceptions.RequestException as e:
        print("API 전송 실패")
        print(e)
        return False