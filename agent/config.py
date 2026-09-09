import os

# API 설정

API_URL = "http://localhost:8000/api/events"

SEND_INTERVAL = 30

REQUEST_TIMEOUT = 5

# Agent / Device 설정

DEVICE_ID = "device01"
LOCATION = "Seoul"


# Agent 인증 정보
# 현재는 기존 테스트 방식도 지원
ACCESS_TOKEN = os.getenv("AGENT_ACCESS_TOKEN")

# A 역할에서 session_id가 구현되면 사용
SESSION_ID = os.getenv("AGENT_SESSION_ID")


def set_agent_auth(access_token, session_id=None):
    """
    로그인 후 전달받은 Agent 인증 정보를 설정한다.
    """

    global ACCESS_TOKEN
    global SESSION_ID

    ACCESS_TOKEN = access_token
    SESSION_ID = session_id