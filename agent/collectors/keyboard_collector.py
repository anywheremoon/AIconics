import threading
import time

from pynput import keyboard


MAX_IDLE_TIME_MS = 3000

MIN_HOLD_TIME_MS = 20
MAX_HOLD_TIME_MS = 1000

MIN_FLIGHT_TIME_MS = 0
MAX_FLIGHT_TIME_MS = 3000


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
    previous_event_time = None
    active_time_seconds = 0.0

    def update_active_time(current_time):
        nonlocal previous_event_time
        nonlocal active_time_seconds

        if previous_event_time is not None:
            gap_seconds = current_time - previous_event_time

            if 0 <= gap_seconds <= MAX_IDLE_TIME_MS / 1000:
                active_time_seconds += gap_seconds

        previous_event_time = current_time

    def on_press(key):
        nonlocal total_keystrokes

        if stop_event.is_set():
            return False

        current_time = time.monotonic()
        update_active_time(current_time)

        # 키를 길게 누를 때 반복되는 down은 제외
        if key in press_times:
            return

        press_times[key] = current_time
        total_keystrokes += 1

        if last_release_time is not None:
            flight_time_ms = (
                current_time - last_release_time
            ) * 1000

            if (
                MIN_FLIGHT_TIME_MS
                <= flight_time_ms
                <= MAX_FLIGHT_TIME_MS
            ):
                flight_times.append(flight_time_ms)

    def on_release(key):
        nonlocal last_release_time

        if stop_event.is_set():
            return False

        current_time = time.monotonic()
        update_active_time(current_time)

        if key in press_times:
            press_time = press_times.pop(key)
            hold_time_ms = (current_time - press_time) * 1000

            if (
                MIN_HOLD_TIME_MS
                <= hold_time_ms
                <= MAX_HOLD_TIME_MS
            ):
                hold_times.append(hold_time_ms)

        last_release_time = current_time

    if stop_event.is_set():
        return {}

    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    )
    listener.start()

    try:
        stop_event.wait(duration)
    finally:
        listener.stop()
        listener.join()

    if stop_event.is_set():
        return {}

    typing_speed = (
        total_keystrokes / active_time_seconds
        if active_time_seconds > 0
        else 0.0
    )

    avg_hold_time = (
        sum(hold_times) / len(hold_times)
        if hold_times
        else 0.0
    )

    avg_flight_time = (
        sum(flight_times) / len(flight_times)
        if flight_times
        else 0.0
    )

    return {
        "typing_speed": round(typing_speed, 2),
        "avg_hold_time": round(avg_hold_time, 2),
        "avg_flight_time": round(avg_flight_time, 2),
        "total_keystrokes": total_keystrokes,
    }


if __name__ == "__main__":
    result = collect_keyboard()
    print("\n키보드 수집 결과")
    print(result)