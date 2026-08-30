from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    primary_device_id: str | None
    usual_ip_subnet: str | None
    usual_location: str | None
    avg_typing_speed: float | None
    avg_hold_time: float | None
    avg_flight_time: float | None
    avg_mouse_move_count: float | None
    avg_click_count: float | None
    event_count: int
    updated_at: datetime
