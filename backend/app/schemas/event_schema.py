from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    device_id: str
    typing_speed: float
    avg_hold_time: float
    avg_flight_time: float
    total_keystrokes: int
    mouse_move_count: int
    click_count: int
    location: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    device_id: str
    ip_address: str
    location: str | None

    typing_speed: float
    avg_hold_time: float
    avg_flight_time: float
    total_keystrokes: int
    mouse_move_count: int
    click_count: int

    is_new_device: bool
    profile_deviation_score: float
    detect_anomaly: bool

    risk_score: float
    risk_level: str

    created_at: datetime


class EventDetectionResponse(BaseModel):
    event_id: int
    risk_score: float
    risk_level: str
    is_anomaly: bool
    profile_deviation_score: float