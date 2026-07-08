from pynput import keyboard
import time


def collect_keyboard(duration=30):
    key_count = 0
    key_times = []

    def on_press(key):
        nonlocal key_count, key_times

        key_count += 1
        key_times.append(time.time())

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    time.sleep(duration)

    listener.stop()

    typing_speed = key_count / (duration / 60)

    if len(key_times) >= 2:
        intervals = []

        for i in range(1, len(key_times)):
            intervals.append(key_times[i] - key_times[i - 1])

        average_key_interval = sum(intervals) / len(intervals)
    else:
        average_key_interval = 0

    return {
        "typing_speed": round(typing_speed, 2),
        "key_count": key_count,
        "average_key_interval": round(average_key_interval, 3)
    }


if __name__ == "__main__":
    result = collect_keyboard()
    print(result)