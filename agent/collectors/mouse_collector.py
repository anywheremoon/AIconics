import math
import threading

from pynput import mouse


def collect_mouse(duration=30, stop_event=None):
    if duration <= 0:
        raise ValueError("duration은 0보다 커야 합니다.")

    if stop_event is None:
        stop_event = threading.Event()

    mouse_move_count = 0
    total_distance = 0.0
    last_position = None

    def on_move(x, y):
        nonlocal mouse_move_count
        nonlocal total_distance
        nonlocal last_position

        if stop_event.is_set():
            return False

        mouse_move_count += 1

        if last_position is not None:
            last_x, last_y = last_position
            total_distance += math.hypot(
                x - last_x,
                y - last_y,
            )

        last_position = (x, y)

    if stop_event.is_set():
        return {}

    listener = mouse.Listener(on_move=on_move)
    listener.start()

    try:
        # 수집 시간이 끝나거나 중지 신호가 오면 대기 종료
        stop_event.wait(duration)
    finally:
        listener.stop()
        listener.join()

    if stop_event.is_set():
        return {}

    return {
        "mouse_move_count": mouse_move_count,
        "mouse_move_distance": round(total_distance, 2),
    }


if __name__ == "__main__":
    print(collect_mouse())