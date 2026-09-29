import os
import threading


# ==========================================
# Backend API 설정
# ==========================================

BACKEND_URL = "http://172.19.20.187:8000"

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

ACCESS_TOKEN = os.getenv("AGENT_ACCESS_TOKEN")
SESSION_ID = os.getenv("AGENT_SESSION_ID")

# 여러 스레드가 인증정보를 일관되게 읽고 변경하도록 보호
_auth_lock = threading.Lock()

# 현재 인증 상태에 연결된 수집 중지 신호
_collection_stop_event = threading.Event()

# 인증정보가 없으면 수집 중지 상태로 시작
if not ACCESS_TOKEN or not SESSION_ID:
    _collection_stop_event.set()


def set_agent_auth(access_token, session_id=None):
    """
    로그인 인증정보를 저장한다.

    기존 수집에는 중지 신호를 보내고,
    새 인증 상태를 위한 별도의 중지 신호를 만든다.
    """
    global ACCESS_TOKEN
    global SESSION_ID
    global _collection_stop_event

    if not isinstance(access_token, str) or not access_token.strip():
        raise ValueError("유효한 access_token이 필요합니다.")

    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("유효한 session_id가 필요합니다.")

    access_token = access_token.strip()
    session_id = session_id.strip()

    with _auth_lock:
        # 이전 인증 상태에서 진행하던 수집을 중단
        _collection_stop_event.set()

        ACCESS_TOKEN = access_token
        SESSION_ID = session_id

        # 이전 신호를 clear하지 않고 새로 생성한다.
        # 빠르게 재로그인해도 이전 수집은 중단 상태를 유지한다.
        _collection_stop_event = threading.Event()


def clear_agent_auth():
    """
    로그아웃 시 기존 수집에 중지 신호를 보내고
    인증정보를 제거한다.
    """
    global ACCESS_TOKEN
    global SESSION_ID

    with _auth_lock:
        _collection_stop_event.set()

        ACCESS_TOKEN = None
        SESSION_ID = None


def get_auth_snapshot():
    """
    같은 시점의 토큰, 세션 ID, 중지 신호를 함께 반환한다.

    main.py는 수집 시작 시 이 값을 받아 사용한다.
    """
    with _auth_lock:
        return (
            ACCESS_TOKEN,
            SESSION_ID,
            _collection_stop_event,
        )


def is_auth_current(access_token, session_id, stop_event):
    """
    수집을 시작할 때의 인증 상태가 여전히 유효한지 확인한다.

    로그아웃 또는 인증정보 재설정이 발생하면 False를 반환한다.
    """
    with _auth_lock:
        return (
            bool(ACCESS_TOKEN)
            and bool(SESSION_ID)
            and ACCESS_TOKEN == access_token
            and SESSION_ID == session_id
            and _collection_stop_event is stop_event
            and not stop_event.is_set()
        )

# ==========================================
# 키보드 + 마우스 학습 데이터 수집
# ==========================================

# 정상 사용 데이터를 수집할 때만 True
# 이상 행동 테스트를 할 때는 False로 변경 후 Agent 재시작
SAVE_TRAINING_DATA = True