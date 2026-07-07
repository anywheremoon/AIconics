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
from collectors.mouse_collector import get_mouse_data
from collectors.click_collector import get_click_data
from collectors.keyboard_collector import get_keyboard_data


def main():

    print("=" * 50)
    print("Behavior Agent Started")
    print("=" * 50)

    # 프로그램이 종료될 때까지 반복
    while True:

        print("\n행동 데이터 수집 중...")

        
        # 행동 데이터 수집
        mouse_data = get_mouse_data()
        click_data = get_click_data()
        keyboard_data = get_keyboard_data()

        # 행동 데이터 하나로 합치기
        behavior_data = {
            **mouse_data,
            **click_data,
            **keyboard_data
        }

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

        # 일정 시간 대기
        wait_seconds(SEND_INTERVAL)


# 프로그램 시작
if __name__ == "__main__":
    main()