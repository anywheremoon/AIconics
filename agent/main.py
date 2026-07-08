import threading

# 설정 파일
from config import SEND_INTERVAL

# Device 정보(C)
from collectors.device_collector import get_device_info

# 시간 함수(C)
from utils.time_utils import get_timestamp, wait_seconds

# JSON 생성(A)
from services.event_buffer import create_event

# API 전송(A)
from services.api_sender import send_event

# 행동 데이터(B)
from collectors.mouse_collector import collect_mouse
from collectors.click_collector import collect_click
from collectors.keyboard_collector import collect_keyboard


def collect_behavior_data(duration=30): # 마우스, 클릭, 키보드 데이터를 동시에 수집하는 함수

    results = {}

    # 각 collector 결과를 저장하는 함수들
    def run_mouse():
        results["mouse"] = collect_mouse(duration)

    def run_click():
        results["click"] = collect_click(duration)

    def run_keyboard():
        results["keyboard"] = collect_keyboard(duration)

    # Thread 생성
    mouse_thread = threading.Thread(target=run_mouse)
    click_thread = threading.Thread(target=run_click)
    keyboard_thread = threading.Thread(target=run_keyboard)

    # 동시에 시작
    mouse_thread.start()
    click_thread.start()
    keyboard_thread.start()

    # 세 작업이 모두 끝날 때까지 대기
    mouse_thread.join()
    click_thread.join()
    keyboard_thread.join()

    # 결과 합치기
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

        # 행동 데이터 30초 동안 동시에 수집
        behavior_data = collect_behavior_data(duration=SEND_INTERVAL)

        # Device 정보 수집
        device_data = get_device_info()

        # 현재 시간
        timestamp = get_timestamp()

        # JSON 생성
        event = create_event(
            behavior_data=behavior_data,
            device_data=device_data,
            timestamp=timestamp
        )

        print("JSON 생성 완료")

        # API 전송
        send_event(event)

        print("서버 전송 완료")
        print(f"{SEND_INTERVAL}초 후 다시 수집합니다.")

        # 이미 collect_behavior_data에서 SEND_INTERVAL만큼 기다렸으므로
        # 여기서는 다시 wait_seconds(SEND_INTERVAL)를 하면 총 60초가 됨
        # 따라서 추가 대기는 하지 않음


# 프로그램 시작 
if __name__ == "__main__":
    main()