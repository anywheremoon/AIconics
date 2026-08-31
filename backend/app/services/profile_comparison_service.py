def _relative_deviation(current, baseline):
    if baseline is None:
        return 0.0

    baseline = float(baseline)
    current = float(current)

    if baseline == 0:
        return 0.0 if current == 0 else 1.0

    return abs(current - baseline) / abs(baseline)


def compare_with_profile(profile, event):
    """
    사용자의 기존 행동 baseline과 현재 이벤트를 비교한다.
    """

    if profile is None:
        return {
            "new_device": False,
            "location_changed": False,
            "typing_deviation": 0.0,
            "hold_time_deviation": 0.0,
            "flight_time_deviation": 0.0,
            "mouse_deviation": 0.0,
            "click_deviation": 0.0,
            "profile_deviation_score": 0,
        }

    new_device = (
        profile.primary_device_id is not None
        and event.device_id != profile.primary_device_id
    )

    location_changed = (
        profile.usual_location is not None
        and event.location is not None
        and event.location != profile.usual_location
    )

    typing_deviation = _relative_deviation(
        event.typing_speed,
        getattr(profile, "avg_typing_speed", None),
    )

    hold_time_deviation = _relative_deviation(
        event.avg_hold_time,
        getattr(profile, "avg_hold_time", None),
    )

    flight_time_deviation = _relative_deviation(
        event.avg_flight_time,
        getattr(profile, "avg_flight_time", None),
    )

    mouse_deviation = _relative_deviation(
        event.mouse_move_count,
        getattr(profile, "avg_mouse_move_count", None),
    )

    click_deviation = _relative_deviation(
        event.click_count,
        getattr(profile, "avg_click_count", None),
    )

    score = 0

    if new_device:
        score += 20

    if location_changed:
        score += 15

    if max(
        typing_deviation,
        hold_time_deviation,
        flight_time_deviation,
    ) >= 0.5:
        score += 15

    if max(
        mouse_deviation,
        click_deviation,
    ) >= 0.5:
        score += 10

    return {
        "new_device": new_device,
        "location_changed": location_changed,
        "typing_deviation": typing_deviation,
        "hold_time_deviation": hold_time_deviation,
        "flight_time_deviation": flight_time_deviation,
        "mouse_deviation": mouse_deviation,
        "click_deviation": click_deviation,
        "profile_deviation_score": min(score, 60),
    }