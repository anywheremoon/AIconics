import config


def create_event(behavior_data, device_data, timestamp):
    """
    행동 데이터와 기기 정보를 하나의 JSON으로 생성
    """

    event = {
        "user_id": config.USER_ID,
        "device_id": device_data.get("device_id", config.DEVICE_ID),
        "ip_address": device_data.get("ip_address"),
        "location": config.LOCATION,
        "timestamp": timestamp,

        "typing_speed": behavior_data.get("typing_speed", 0),
        "mouse_move_count": behavior_data.get("mouse_move_count", 0),
        "click_count": behavior_data.get("click_count", 0),

        "is_new_device": device_data.get("is_new_device", False),

        "os": device_data.get("os"),
        "cpu": device_data.get("cpu"),
        "ram": device_data.get("ram")
    }

    return event