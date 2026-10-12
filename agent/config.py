import os
import threading


# ==========================================
# Backend API 设置
# ==========================================

BACKEND_URL = "http://192.168.45.9:8000"
API_URL = f"{BACKEND_URL}/api/events"

SEND_INTERVAL = 30
REQUEST_TIMEOUT = 5


# ==========================================
# Agent / Device 设置
# ==========================================

DEVICE_ID = "device01"
LOCATION = "Seoul"


# ==========================================
# Agent 认证信息
# ==========================================

ACCESS_TOKEN = os.getenv("AGENT_ACCESS_TOKEN")
SESSION_ID = os.getenv("AGENT_SESSION_ID")

_auth_lock = threading.Lock()
_auth_version = 0
_collection_stop_events = set()


def _stop_collections_locked():
    """调用时必须已经持有 _auth_lock。"""

    for stop_event in _collection_stop_events:
        stop_event.set()


def get_auth_snapshot():
    """一次性读取匹配的令牌、会话和认证版本。"""

    with _auth_lock:
        return ACCESS_TOKEN, SESSION_ID, _auth_version


def auth_is_current(access_token, session_id, version):
    with _auth_lock:
        return (
            bool(ACCESS_TOKEN)
            and bool(SESSION_ID)
            and ACCESS_TOKEN == access_token
            and SESSION_ID == session_id
            and _auth_version == version
        )


def set_agent_auth(access_token, session_id=None):
    """保存认证；认证变化时停止旧收集。"""

    global ACCESS_TOKEN, SESSION_ID, _auth_version

    if not isinstance(access_token, str) or not access_token.strip():
        raise ValueError("有效的 access_token 是必需的。")

    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("有效的 session_id 是必需的。")

    access_token = access_token.strip()
    session_id = session_id.strip()

    with _auth_lock:
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
    """清除认证，并停止正在进行的收集。"""

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
    """只清除失败请求对应的认证，保留后续的新登录。"""

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
    """原子地取得认证快照并注册中止信号。"""

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
    with _auth_lock:
        _collection_stop_events.discard(stop_event)