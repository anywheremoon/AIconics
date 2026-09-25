import os


# ==========================================
# Backend API 설정
# ==========================================

BACKEND_URL = "http://172.19.27.182:8000"

API_URL = f"{BACKEND_URL}/api/events"

SEND_INTERVAL = 30

REQUEST_TIMEOUT = 5


# ==========================================
# Agent / Device 설정
# ==========================================

DEVICE_ID = "device01"
LOCATION = "Seoul"


# ==========================================
# Agent 인증 정보
# ==========================================

ACCESS_TOKEN = os.getenv(
    "AGENT_ACCESS_TOKEN"
)

SESSION_ID = os.getenv(
    "AGENT_SESSION_ID"
)


def set_agent_auth(
    access_token,
    session_id=None
):
    """
    로그인 후 전달받은 Agent 인증 정보를 설정한다.
    """

    global ACCESS_TOKEN
    global SESSION_ID

    ACCESS_TOKEN = access_token
    SESSION_ID = session_id


def clear_agent_auth():
    """
    로그아웃 시 Agent 인증 정보를 제거한다.
    """

    global ACCESS_TOKEN
    global SESSION_ID

    ACCESS_TOKEN = None
    SESSION_ID = None