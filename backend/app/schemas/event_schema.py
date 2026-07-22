from pydantic import BaseModel
from typing import Optional


class EventCreate(BaseModel):
    user_id: str
    device_id: str
    ip_address: str
    location: Optional[str] = None

    # 키보드 ML Feature
    typing_speed: float
    avg_hold_time: float
    avg_flight_time: float
    total_keystrokes: int

    # 기존 규칙 기반 Feature
    mouse_move_count: int
    click_count: int

    is_new_device: bool = False