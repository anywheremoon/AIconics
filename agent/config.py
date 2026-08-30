import os

API_URL = "http://localhost:8000/api/events"

SEND_INTERVAL = 30

# 기존 호환용
USER_ID = "user01"

DEVICE_ID = "device01"
LOCATION = "Seoul"

REQUEST_TIMEOUT = 5

# 6단계 Agent 인증용
ACCESS_TOKEN = os.getenv("AGENT_ACCESS_TOKEN")