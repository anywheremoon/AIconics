import threading
import time

from pynput import keyboard


def collect_keyboard(duration=30, stop_event=None):
    if duration <= 0:
        raise ValueError("duration은 0보다 커야 합니다.")

    if stop_event is None:
        stop_event = threading.Event()

    total_keystrokes = 0
    press_times = {}
    hold_times = []
    flight_times = []
    last_release_time = None

    def on_press(key):
        nonlocal total_keystrokes

        if stop_event.is_set():
            return False

        current_time = time.monotonic()

        # OS key repeat 중복 계산 방지
        if key in press_times:
            return

        press_times[key] = current_time
        total_keystrokes += 1

        if last_release_time is not None:
            flight_time = current_time - last_release_time

            if flight_time >= 0:
                flight_times.append(flight_time * 1000)

    def on_release(key):
        nonlocal last_release_time

        if stop_event.is_set():
            return False

        current_time = time.monotonic()

        if key in press_times:
            press_time = press_times.pop(key)
            hold_time = current_time - press_time

            if hold_time >= 0:
                hold_times.append(hold_time * 1000)

        last_release_time = current_time

    if not stop_event.is_set():
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release,
        )

        listener.start()

        try:
            print(
                f"{duration}초 동안 키보드 입력을 수집합니다..."
            )

            stop_event.wait(timeout=duration)
        finally:
            listener.stop()
            listener.join()

    # 기존 단위 유지: 분당 키 입력 수
    # 중도 취소된 수집 결과는 main.py에서 폐기해야 한다.
    typing_speed = total_keystrokes / (duration / 60)

    avg_hold_time = (
        sum(hold_times) / len(hold_times)
        if hold_times
        else 0
    )

    avg_flight_time = (
        sum(flight_times) / len(flight_times)
        if flight_times
        else 0
    )

    return {
        "typing_speed": round(typing_speed, 2),
        "avg_hold_time": round(avg_hold_time, 2),
        "avg_flight_time": round(avg_flight_time, 2),
        "total_keystrokes": total_keystrokes,
    }


if __name__ == "__main__":
    print("\n키보드 수집 결과")
    print(collect_keyboard())