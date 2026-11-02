import os
import threading


# ==========================================
# Backend API 설정
# ==========================================

BACKEND_URL = "http://192.168.45.9:8000"
API_URL = f"{BACKEND_URL}/api/events"

SEND_INTERVAL = 30
REQUEST_TIMEOUT = 5


# ==========================================
# Agent / Device 설정
# ==========================================

DEVICE_ID = "device01"
LOCATION = "Seoul"


# ==========================================
# Agent 인증정보
# ==========================================

ACCESS_TOKEN = os.getenv("AGENT_ACCESS_TOKEN")
SESSION_ID = os.getenv("AGENT_SESSION_ID")

_auth_lock = threading.Lock()
_auth_version = 0
_collection_stop_events = set()


def _stop_collections_locked():
    """인증정보 잠금을 획득한 상태에서 수집 중지 신호를 보낸다."""

    for stop_event in _collection_stop_events:
        stop_event.set()


def get_auth_snapshot():
    """토큰, 세션 ID, 인증 버전을 함께 조회한다."""

    with _auth_lock:
        return ACCESS_TOKEN, SESSION_ID, _auth_version


def auth_is_current(access_token, session_id, version):
    """수집 시작 시점의 인증정보가 현재도 유효한지 확인한다."""

    with _auth_lock:
        return (
            bool(ACCESS_TOKEN)
            and bool(SESSION_ID)
            and ACCESS_TOKEN == access_token
            and SESSION_ID == session_id
            and _auth_version == version
        )


def set_agent_auth(access_token, session_id=None):
    """인증정보를 저장하고, 변경 시 이전 수집을 중지한다."""

    global ACCESS_TOKEN, SESSION_ID, _auth_version

    if (
        not isinstance(access_token, str)
        or not access_token.strip()
    ):
        raise ValueError(
            "유효한 access_token이 필요합니다."
        )

    if (
        not isinstance(session_id, str)
        or not session_id.strip()
    ):
        raise ValueError(
            "유효한 session_id가 필요합니다."
        )

    access_token = access_token.strip()
    session_id = session_id.strip()

    with _auth_lock:
        # 동일한 인증정보를 다시 받으면 기존 수집 유지
        if (
            ACCESS_TOKEN == access_token
            and SESSION_ID == session_id
        ):
            return

        _stop_collections_locked()

        ACCESS_TOKEN = access_token
        SESSION_ID = session_id
        _auth_version += 1


def clear_agent_auth():
    """인증정보를 제거하고 진행 중인 수집을 중지한다."""

    global ACCESS_TOKEN, SESSION_ID, _auth_version

    with _auth_lock:
        _stop_collections_locked()

        ACCESS_TOKEN = None
        SESSION_ID = None
        _auth_version += 1


def clear_agent_auth_if_current(
    access_token,
    session_id,
    version,
):
    """실패한 요청의 인증만 제거하고 이후의 새 로그인은 유지한다."""

    global ACCESS_TOKEN, SESSION_ID, _auth_version

    with _auth_lock:
        if (
            ACCESS_TOKEN != access_token
            or SESSION_ID != session_id
            or _auth_version != version
        ):
            return False

        _stop_collections_locked()

        ACCESS_TOKEN = None
        SESSION_ID = None
        _auth_version += 1

        return True


def begin_collection():
    """인증정보 조회와 수집 중지 신호 등록을 함께 처리한다."""

    with _auth_lock:
        if not ACCESS_TOKEN or not SESSION_ID:
            return None

        stop_event = threading.Event()
        _collection_stop_events.add(stop_event)

        return (
            ACCESS_TOKEN,
            SESSION_ID,
            _auth_version,
            stop_event,
        )


def end_collection(stop_event):
    """완료된 수집의 중지 신호 등록을 해제한다."""

    with _auth_lock:
        _collection_stop_events.discard(stop_event)