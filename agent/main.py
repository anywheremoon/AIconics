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
from services.training_data_logger import save_training_sample


def collect_behavior_data(duration, stop_event):
    """마우스, 클릭, 키보드 데이터를 동시에 수집한다."""

    if stop_event.is_set():
        return None

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            "mouse": executor.submit(
                collect_mouse,
                duration=duration,
                stop_event=stop_event,
            ),
            "click": executor.submit(
                collect_click,
                duration=duration,
                stop_event=stop_event,
            ),
            "keyboard": executor.submit(
                collect_keyboard,
                duration=duration,
                stop_event=stop_event,
            ),
        }

        # 수집기에서 예외가 발생하면 main으로 전달
        results = {
            name: future.result()
            for name, future in futures.items()
        }

    if stop_event.is_set():
        return None

    if any(not result for result in results.values()):
        raise RuntimeError("일부 수집기의 결과가 없습니다.")

    return {
        **results["mouse"],
        **results["click"],
        **results["keyboard"],
    }


def main():
    print("=" * 50)
    print("Behavior Agent Started")
    print("=" * 50)

    start_auth_receiver()

    waiting_logged = False

    try:
        while True:
            # 같은 시점의 인증정보와 중지 신호 확보
            access_token, session_id, stop_event = (
                config.get_auth_snapshot()
            )

            if (
                not access_token
                or not session_id
                or stop_event.is_set()
            ):
                if not waiting_logged:
                    print("사용자 로그인 인증정보를 기다리는 중...")
                    waiting_logged = True

                time.sleep(0.2)
                continue

            waiting_logged = False

            print(f"\n행동 데이터 수집 시작: {session_id}")

            try:
                # 이번 수집에 사용할 시간을 고정
                duration = config.SEND_INTERVAL

                behavior_data = collect_behavior_data(
                    duration=duration,
                    stop_event=stop_event,
                )

                # 중단되었거나 인증 상태가 바뀌면 결과 폐기
                if (
                    behavior_data is None
                    or not config.is_auth_current(
                        access_token,
                        session_id,
                        stop_event,
                    )
                ):
                    print(
                        "로그아웃 또는 인증 상태 변경 - "
                        "수집 결과를 폐기합니다."
                    )
                    continue

                # ==========================================
                # 키보드 + 마우스 학습용 CSV 저장
                # ==========================================
                if config.SAVE_TRAINING_DATA:
                    try:
                        if config.is_auth_current(
                            access_token,
                            session_id,
                            stop_event,
                        ):
                            saved_path = save_training_sample(
                                behavior_data=behavior_data,
                                duration=duration,
                            )

                            print(
                                f"학습 데이터 CSV 저장: {saved_path}"
                            )

                    except Exception as error:
                        # CSV 저장 실패와 기존 이벤트 전송을 분리
                        print(
                            f"학습 데이터 저장 실패: {error}"
                        )

                # CSV 저장 중 인증 상태가 변경되었는지 확인
                if not config.is_auth_current(
                    access_token,
                    session_id,
                    stop_event,
                ):
                    print(
                        "로그아웃 또는 인증 상태 변경 - "
                        "이벤트 전송을 취소합니다."
                    )
                    continue

                # ==========================================
                # Backend 전송용 이벤트 생성
                # ==========================================
                device_data = get_device_info()
                timestamp = get_timestamp()

                event = create_event(
                    behavior_data=behavior_data,
                    device_data=device_data,
                    timestamp=timestamp,
                )

                # 수집 시작 당시의 세션 연결
                event["session_id"] = session_id

                # ==========================================
                # Backend 전송
                # ==========================================
                success = send_event(
                    event,
                    access_token=access_token,
                    session_id=session_id,
                    stop_event=stop_event,
                )

                if success:
                    print("서버 전송 완료")
                else:
                    print("서버 전송 취소 또는 실패")

            except Exception as error:
                print(f"행동 데이터 처리 실패: {error}")

                # 반복 오류 시 과도한 재시도 방지
                # 로그아웃 신호가 오면 대기 종료
                stop_event.wait(1)

    except KeyboardInterrupt:
        print("\nAgent를 종료합니다.")

    finally:
        config.clear_agent_auth()


if __name__ == "__main__":
    main()