import requests
import config


def send_event(event):
    """
    FastAPI 서버로 이벤트 전송
    """

    try:
        response = requests.post(
            config.API_URL,
            json=event,
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