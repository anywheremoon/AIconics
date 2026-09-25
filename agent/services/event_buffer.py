import config


def create_event(behavior_data, device_data, timestamp):
    """
    행동 데이터와 기기 정보를 하나의 Event JSON으로 생성
    """

    event = {
        # Device 정보
        "device_id": device_data.get(
            "device_id",
            config.DEVICE_ID
        ),
        "ip_address": device_data.get("ip_address"),
        "location": config.LOCATION,

        # Event 발생 시간
        "timestamp": timestamp,

        # Keyboard 행동 데이터
        "typing_speed": behavior_data.get(
            "typing_speed",
            0.0
        ),
        "avg_hold_time": behavior_data.get(
            "avg_hold_time",
            0.0
        ),
        "avg_flight_time": behavior_data.get(
            "avg_flight_time",
            0.0
        ),
        "total_keystrokes": behavior_data.get(
            "total_keystrokes",
            0
        ),

        # Mouse / Click 행동 데이터
        "mouse_move_count": behavior_data.get(
            "mouse_move_count",
            0
        ),
        "click_count": behavior_data.get(
            "click_count",
            0
        ),

        # Device 추가 정보
        "is_new_device": device_data.get(
            "is_new_device",
            False
        ),

        "os": device_data.get("os"),
        "cpu": device_data.get("cpu"),
        "ram": device_data.get("ram")
    }

    # 로그인 Session이 존재하는 경우 추가
    if config.SESSION_ID:
        event["session_id"] = config.SESSION_ID

    return event