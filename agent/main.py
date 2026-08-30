import json
import threading

# 설정
from config import SEND_INTERVAL

# Device 정보
from collectors.device_collector import get_device_info

# 시간 함수
from utils.time_utils import get_timestamp

# 최종 Event JSON 생성
from services.event_buffer import create_event

# API 전송
from services.api_sender import send_event

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

    mouse_thread = threading.Thread(target=run_mouse)
    click_thread = threading.Thread(target=run_click)
    keyboard_thread = threading.Thread(target=run_keyboard)

    mouse_thread.start()
    click_thread.start()
    keyboard_thread.start()

    mouse_thread.join()
    click_thread.join()
    keyboard_thread.join()

    behavior_data = {
        **results["mouse"],
        **results["click"],
        **results["keyboard"]
    }

    return behavior_data


def main():

    print("=" * 50)
    print("Behavior Agent Started")
    print("=" * 50)

    while True:

        print("\n행동 데이터 수집 중...")

        # SEND_INTERVAL 동안 행동 데이터 동시 수집
        behavior_data = collect_behavior_data(
            duration=SEND_INTERVAL
        )

        # Device 정보 수집
        device_data = get_device_info()

        # 현재 시간
        timestamp = get_timestamp()

        # 서버 전송용 Event 생성
        event = create_event(
            behavior_data=behavior_data,
            device_data=device_data,
            timestamp=timestamp
        )

        print("JSON 생성 완료")

        print(
            json.dumps(
                event,
                indent=4,
                ensure_ascii=False
            )
        )

        # API 전송
        success = send_event(event)

        if success:
            print("서버 전송 완료")
        else:
            print("서버 전송 실패")

        print("다음 행동 데이터를 수집합니다.")


if __name__ == "__main__":
    main()