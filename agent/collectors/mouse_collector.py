from pynput import mouse
import time
import math


def collect_mouse(duration=30):
    mouse_move_count = 0
    total_distance = 0.0
    last_position = None

    def on_move(x, y):
        nonlocal mouse_move_count, total_distance, last_position

        mouse_move_count += 1

        if last_position is not None:
            last_x, last_y = last_position
            distance = math.sqrt((x - last_x) ** 2 + (y - last_y) ** 2)
            total_distance += distance

        last_position = (x, y)

    listener = mouse.Listener(on_move=on_move)
    listener.start()

    time.sleep(duration)

    listener.stop()

    return {
        "mouse_move_count": mouse_move_count,
        "mouse_move_distance": round(total_distance, 2)
    }


if __name__ == "__main__":
    result = collect_mouse()
    print(result)