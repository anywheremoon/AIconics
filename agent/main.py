import json
import time
from concurrent.futures import ThreadPoolExecutor

import config

from collectors.device_collector import get_device_info
from collectors.mouse_collector import collect_mouse
from collectors.click_collector import collect_click
from collectors.keyboard_collector import collect_keyboard

from utils.time_utils import get_timestamp

from services.event_buffer import create_event
from services.api_sender import send_event
from services.auth_receiver import start_auth_receiver


def collect_behavior_data(duration=30):
    """마우스, 클릭, 키보드 데이터를 동시에 수집한다."""

    with ThreadPoolExecutor(max_workers=3) as executor:
        mouse_future = executor.submit(collect_mouse, duration)
        click_future = executor.submit(collect_click, duration)
        keyboard_future = executor.submit(collect_keyboard, duration)

        mouse_data = mouse_future.result()
        click_data = click_future.result()
        keyboard_data = keyboard_future.result()

    return {
        **mouse_data,
        **click_data,
        **keyboard_data,
    }


def auth_is_unchanged(access_token, session_id):
    """수집 시작 시점의 인증정보가 유지되는지 확인한다."""

    return (
        bool(config.ACCESS_TOKEN)
        and bool(config.SESSION_ID)
        and config.ACCESS_TOKEN == access_token
        and config.SESSION_ID == session_id
    )


def main():
    print("=" * 50)
    print("Behavior Agent Started")
    print("=" * 50)

    start_auth_receiver()

    last_auth_state = None

    while True:
        # 로그인 전에는 수집하지 않고 대기한다.
        if not config.ACCESS_TOKEN:
            if last_auth_state != "WAITING_TOKEN":
                print("사용자 로그인 인증정보를 기다리는 중...")
                last_auth_state = "WAITING_TOKEN"

            time.sleep(1)
            continue

        # Session ID가 없으면 대기한다.
        if not config.SESSION_ID:
            if last_auth_state != "WAITING_SESSION":
                print("Session ID를 기다리는 중...")
                last_auth_state = "WAITING_SESSION"

            time.sleep(1)
            continue

        collection_token = config.ACCESS_TOKEN
        collection_session = config.SESSION_ID

        current_auth_state = (
            "AUTHENTICATED",
            collection_session,
        )

        # 같은 Session에서는 인증 완료 메시지를 한 번만 출력한다.
        if last_auth_state != current_auth_state:
            print("\nAgent 인증 완료")
            print(f"Session ID : {collection_session}")
            last_auth_state = current_auth_state

        print("\n행동 데이터 수집 중...")

        try:
            behavior_data = collect_behavior_data(
                duration=config.SEND_INTERVAL
            )

            # 수집 중 로그아웃 또는 인증정보 변경 시 데이터를 폐기한다.
            if not auth_is_unchanged(
                collection_token,
                collection_session,
            ):
                print(
                    "인증정보 변경 감지 - "
                    "수집한 데이터는 전송하지 않습니다."
                )
                continue

            device_data = get_device_info()
            timestamp = get_timestamp()

            event = create_event(
                behavior_data=behavior_data,
                device_data=device_data,
                timestamp=timestamp,
            )

            event["session_id"] = collection_session

            print("JSON 생성 완료")
            print(
                json.dumps(
                    event,
                    indent=4,
                    ensure_ascii=False,
                )
            )

            # 서버 전송 직전에 인증정보를 다시 확인한다.
            if not auth_is_unchanged(
                collection_token,
                collection_session,
            ):
                print(
                    "인증정보 변경 감지 - "
                    "서버 전송을 중단합니다."
                )
                continue

            success = send_event(event)

            if success:
                print("서버 전송 완료")
            else:
                print("서버 전송 실패")

            print("다음 행동 데이터를 수집합니다.")

        except Exception as error:
            print(f"행동 데이터 수집 또는 전송 오류: {error}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBehavior Agent 종료")