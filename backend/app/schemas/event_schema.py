from pydantic import BaseModel
from typing import Optional


class EventCreate(BaseModel):
    user_id: str
    device_id: str
    ip_address: str
    location: Optional[str] = None
    typing_speed: float
    mouse_move_count: int
    click_count: int
    is_new_device: bool = False