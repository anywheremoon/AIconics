import threading

from pynput import mouse


def collect_click(duration=30, stop_event=None):
    if stop_event is None:
        stop_event = threading.Event()

    left_click_count = 0
    right_click_count = 0
    total_click_count = 0

    def on_click(x, y, button, pressed):
        nonlocal left_click_count
        nonlocal right_click_count
        nonlocal total_click_count

        if stop_event.is_set():
            return False

        if pressed:
            total_click_count += 1

            if button == mouse.Button.left:
                left_click_count += 1
            elif button == mouse.Button.right:
                right_click_count += 1

    if not stop_event.is_set():
        listener = mouse.Listener(on_click=on_click)
        listener.start()

        try:
            stop_event.wait(timeout=duration)
        finally:
            listener.stop()
            listener.join()

    return {
        "left_click_count": left_click_count,
        "right_click_count": right_click_count,
        "click_count": total_click_count,
    }


if __name__ == "__main__":
    print(collect_click())