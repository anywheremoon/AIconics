import json
import threading
import time

import config

# Device 정보
from collectors.device_collector import get_device_info

# 시간 함수
from utils.time_utils import get_timestamp

# 최종 Event JSON 생성
from services.event_buffer import create_event

# API 전송
from services.api_sender import send_event

# 로그인 인증정보 수신
from services.auth_receiver import start_auth_receiver

# 행동 데이터 수집
from collectors.mouse_collector import collect_mouse
from collectors.click_collector import collect_click
from collectors.keyboard_collector import collect_keyboard


def collect_behavior_data(duration=30):
    """
    마우스, 클릭, 키보드 데이터를 동시에 수집
    """

    results = {}

    def run_mouse():
        results["mouse"] = collect_mouse(duration)

    def run_click():
        results["click"] = collect_click(duration)

    def run_keyboard():
        results["keyboard"] = collect_keyboard(duration)

    mouse_thread = threading.Thread(
        target=run_mouse
    )

    click_thread = threading.Thread(
        target=run_click
    )

    keyboard_thread = threading.Thread(
        target=run_keyboard
    )

    mouse_thread.start()
    click_thread.start()
    keyboard_thread.start()

    mouse_thread.join()
    click_thread.join()
    keyboard_thread.join()

    behavior_data = {
        **results.get("mouse", {}),
        **results.get("click", {}),
        **results.get("keyboard", {})
    }

    return behavior_data


def main():

    print("=" * 50)
    print("Behavior Agent Started")
    print("=" * 50)

    # -------------------------------------------------
    # 로그인 인증정보를 받을 로컬 서버 시작
    # -------------------------------------------------

    start_auth_receiver()

    # -------------------------------------------------
    # 프론트 로그인 정보 대기
    # -------------------------------------------------

    if not config.ACCESS_TOKEN:

        print("사용자 로그인 인증정보를 기다리는 중...")

        while not config.ACCESS_TOKEN:
            time.sleep(1)

    print("Agent 인증 완료")

    if config.SESSION_ID:
        print(
            f"Session ID : {config.SESSION_ID}"
        )
    else:
        print(
            "Session ID가 설정되지 않았습니다."
        )

    # -------------------------------------------------
    # 행동 데이터 지속 수집
    # -------------------------------------------------

    while True:

        print("\n행동 데이터 수집 중...")

        behavior_data = collect_behavior_data(
            duration=config.SEND_INTERVAL
        )

        # Device 정보
        device_data = get_device_info()

        # 시간
        timestamp = get_timestamp()

        # Event JSON 생성
        event = create_event(
            behavior_data=behavior_data,
            device_data=device_data,
            timestamp=timestamp
        )

        # 현재 로그인 Session 연결
        if config.SESSION_ID:
            event["session_id"] = (
                config.SESSION_ID
            )

        print("JSON 생성 완료")

        print(
            json.dumps(
                event,
                indent=4,
                ensure_ascii=False
            )
        )

        # 서버 전송
        success = send_event(event)

        if success:
            print("서버 전송 완료")
        else:
            print("서버 전송 실패")

        print(
            "다음 행동 데이터를 수집합니다."
        )


if __name__ == "__main__":
    main()