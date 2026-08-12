from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    primary_device_id: str
    usual_ip_subnet: str | None
    usual_location: str | None
    event_count: int
    updated_at: datetime
