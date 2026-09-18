from pynput import keyboard
import time


def collect_keyboard(duration=30):
    # 전체 키 입력 수
    total_keystrokes = 0

    # 각 키가 눌린 시간을 저장
    press_times = {}

    # Hold Time 목록
    hold_times = []

    # Flight Time 목록
    flight_times = []

    # 직전에 뗀 키의 시간
    last_release_time = None

    # 전체 입력 시작/종료 기준
    first_press_time = None
    last_press_time = None


    def on_press(key):
        nonlocal total_keystrokes
        nonlocal last_release_time
        nonlocal first_press_time
        nonlocal last_press_time

        current_time = time.time()

        # 같은 키를 계속 누르고 있을 때
        # OS key repeat 때문에 중복 계산되는 것 방지
        if key in press_times:
            return

        press_times[key] = current_time
        total_keystrokes += 1

        # 첫 번째 키 입력 시간
        if first_press_time is None:
            first_press_time = current_time

        last_press_time = current_time

        # Flight Time 계산
        # 이전 키를 뗀 후 다음 키를 누르기까지 걸린 시간
        if last_release_time is not None:
            flight_time = current_time - last_release_time

            # ms 단위 저장
            if flight_time >= 0:
                flight_times.append(flight_time * 1000)


    def on_release(key):
        nonlocal last_release_time

        current_time = time.time()

        # 해당 키의 press 시간이 존재하는 경우
        if key in press_times:
            press_time = press_times.pop(key)

            # Hold Time 계산
            hold_time = current_time - press_time

            if hold_time >= 0:
                hold_times.append(hold_time * 1000)

        last_release_time = current_time


    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )

    listener.start()

    print(f"{duration}초 동안 키보드 입력을 수집합니다...")

    time.sleep(duration)

    listener.stop()
    listener.join()


    # -----------------------------
    # Typing Speed 계산
    # -----------------------------
    # 기존 프로젝트 형식대로 분당 키 입력 수
    if total_keystrokes > 0:
        typing_speed = total_keystrokes / (duration / 60)
    else:
        typing_speed = 0


    # -----------------------------
    # 평균 Hold Time
    # -----------------------------
    if hold_times:
        avg_hold_time = sum(hold_times) / len(hold_times)
    else:
        avg_hold_time = 0


    # -----------------------------
    # 평균 Flight Time
    # -----------------------------
    if flight_times:
        avg_flight_time = sum(flight_times) / len(flight_times)
    else:
        avg_flight_time = 0


    return {
        "typing_speed": round(typing_speed, 2),
        "avg_hold_time": round(avg_hold_time, 2),
        "avg_flight_time": round(avg_flight_time, 2),
        "total_keystrokes": total_keystrokes
    }


if __name__ == "__main__":
    result = collect_keyboard()

    print("\n키보드 수집 결과")
    print(result)
