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


def collect_behavior_data(duration, stop_event):
    """동시에 행동 데이터를 수집하고, 중지되면 결과를 폐기한다."""

    if stop_event.is_set():
        return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(
                collect_mouse,
                duration=duration,
                stop_event=stop_event,
            ),
            executor.submit(
                collect_click,
                duration=duration,
                stop_event=stop_event,
            ),
            executor.submit(
                collect_keyboard,
                duration=duration,
                stop_event=stop_event,
            ),
        ]

        try:
            results = [
                future.result()
                for future in futures
            ]
        except BaseException:
            stop_event.set()
            raise

    if stop_event.is_set():
        return None

    return {
        **results[0],
        **results[1],
        **results[2],
    }


def main():
    print("=" * 50)
    print("행동 데이터 Agent 시작")
    print("=" * 50)

    start_auth_receiver()

    last_auth_state = None

    while True:
        # 인증정보 조회와 수집 중지 신호 등록
        collection = config.begin_collection()

        if collection is None:
            if last_auth_state != "WAITING_AUTH":
                print("사용자 로그인 인증정보를 기다리는 중...")
                last_auth_state = "WAITING_AUTH"

            time.sleep(0.5)
            continue

        (
            collection_token,
            collection_session,
            collection_version,
            stop_event,
        ) = collection

        current_auth_state = (
            collection_session,
            collection_version,
        )

        if last_auth_state != current_auth_state:
            print("\nAgent 인증 완료")
            print(f"Session ID : {collection_session}")
            last_auth_state = current_auth_state

        try:
            print("\n행동 데이터 수집 중...")

            behavior_data = collect_behavior_data(
                duration=config.SEND_INTERVAL,
                stop_event=stop_event,
            )

            # 로그아웃 또는 인증 변경 시 수집 결과 폐기
            if (
                behavior_data is None
                or not config.auth_is_current(
                    collection_token,
                    collection_session,
                    collection_version,
                )
            ):
                print(
                    "인증정보 변경 감지 - "
                    "수집을 중지하고 데이터를 폐기했습니다."
                )
                continue

            event = create_event(
                behavior_data=behavior_data,
                device_data=get_device_info(),
                timestamp=get_timestamp(),
            )

            event["session_id"] = collection_session

            # 이벤트 생성 중 인증이 변경됐는지 재확인
            if (
                stop_event.is_set()
                or not config.auth_is_current(
                    collection_token,
                    collection_session,
                    collection_version,
                )
            ):
                print(
                    "인증정보 변경 감지 - "
                    "이벤트를 전송하지 않습니다."
                )
                continue

            print("JSON 생성 완료")
            print(
                json.dumps(
                    event,
                    indent=4,
                    ensure_ascii=False,
                )
            )

            # 수집 시작 시점의 토큰과 세션으로 전송
            success = send_event(
                event,
                access_token=collection_token,
                session_id=collection_session,
                auth_version=collection_version,
            )

            if success:
                print("서버 전송 완료")
            else:
                print("서버 전송 실패 또는 전송 취소")

        except Exception as error:
            print(
                f"행동 데이터 수집 또는 전송 오류: {error}"
            )
            time.sleep(1)

        finally:
            # 종료·예외 상황에서도 수집 중지 및 등록 해제
            stop_event.set()
            config.end_collection(stop_event)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        config.clear_agent_auth()
        print("\n행동 데이터 Agent 종료")