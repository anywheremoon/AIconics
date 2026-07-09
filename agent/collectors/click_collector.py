from pynput import mouse
import time


def collect_click(duration=30):
    left_click_count = 0
    right_click_count = 0
    total_click_count = 0

    def on_click(x, y, button, pressed):
        nonlocal left_click_count, right_click_count, total_click_count

        if pressed:
            total_click_count += 1

            if button == mouse.Button.left:
                left_click_count += 1
            elif button == mouse.Button.right:
                right_click_count += 1

    listener = mouse.Listener(on_click=on_click)
    listener.start()

    time.sleep(duration)

    listener.stop()

    return {
        "left_click_count": left_click_count,
        "right_click_count": right_click_count,
        "click_count": total_click_count
    }


if __name__ == "__main__":
    result = collect_click()
    print(result)