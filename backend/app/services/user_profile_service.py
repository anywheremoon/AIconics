import ipaddress
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import user_profile_repository


PROFILE_READY_EVENT_COUNT = 10
BEHAVIOR_FIELDS = (
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "mouse_move_count",
    "click_count",
)


def _to_subnet(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    try:
        address = ipaddress.ip_address(ip_address)
    except ValueError:
        return None
    prefix = 24 if address.version == 4 else 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


def create_initial_profile(
    db: Session,
    user_id: int,
    device_id: str,
    ip_address: str | None,
    location: str | None,
):
    return user_profile_repository.create_profile(
        db,
        {
            "user_id": user_id,
            "primary_device_id": device_id,
            "usual_ip_subnet": _to_subnet(ip_address),
            "usual_location": location,
            "event_count": 0,
        },
    )


def get_user_baseline(db: Session, user_id: int):
    return user_profile_repository.find_by_user_id(db, user_id)


def get_my_profile(db: Session, user_id: int):
    return get_user_baseline(db, user_id)


def _event_value(event: Any, field: str) -> float:
    value = event.get(field) if isinstance(event, Mapping) else getattr(event, field, None)
    if value is None:
        raise ValueError(f"Behavior event is missing required field: {field}")
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Behavior event field must be numeric: {field}") from error
    if numeric_value < 0:
        raise ValueError(f"Behavior event field cannot be negative: {field}")
    return numeric_value


def _running_average(current: float | None, value: float, event_count: int) -> float:
    # A migrated profile can have an event count but no behavioral averages yet.
    if current is None:
        return value
    return ((current * event_count) + value) / (event_count + 1)


def update_behavior_profile(db: Session, user_id: int, event: Any):
    """Update all behavioral baselines from one event using running averages.

    Transaction ownership remains with the caller so event persistence, risk
    calculation, and profile learning can be committed atomically.
    """
    profile = get_user_baseline(db, user_id)
    if profile is None:
        return None

    values = {field: _event_value(event, field) for field in BEHAVIOR_FIELDS}
    count = profile.event_count
    user_profile_repository.update_behavior_profile(
        db,
        user_id,
        avg_typing_speed=_running_average(profile.avg_typing_speed, values["typing_speed"], count),
        avg_hold_time=_running_average(profile.avg_hold_time, values["avg_hold_time"], count),
        avg_flight_time=_running_average(profile.avg_flight_time, values["avg_flight_time"], count),
        avg_mouse_move_count=_running_average(
            profile.avg_mouse_move_count, values["mouse_move_count"], count
        ),
        avg_click_count=_running_average(profile.avg_click_count, values["click_count"], count),
    )
    return user_profile_repository.increment_event_count(db, user_id)


def is_profile_ready(
    db: Session,
    user_id: int,
    minimum_event_count: int = PROFILE_READY_EVENT_COUNT,
) -> bool:
    profile = get_user_baseline(db, user_id)
    return profile is not None and profile.event_count >= minimum_event_count


def update_profile_event_count(db: Session, user_id: int):
    """Compatibility wrapper for code that only records an event count."""
    return user_profile_repository.increment_event_count(db, user_id)
