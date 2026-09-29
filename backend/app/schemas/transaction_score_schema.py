from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionRiskRequest(BaseModel):
    session_id: UUID
    recipient_account_number: str = Field(pattern=r"^\d{12}$")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class TransactionRiskResponse(BaseModel):
    transaction_score: int = Field(ge=0, le=100)
    is_new_recipient: bool
    account_age_days: int = Field(ge=0)
    minutes_after_login: float = Field(ge=0)
    is_high_amount: bool
    is_unusually_large: bool
    is_new_account_high_amount: bool
    is_rapid_balance_drain: bool
    average_transfer_amount: Decimal | None
    recent_10_minute_count: int = Field(ge=0)
    projected_10_minute_count: int = Field(ge=1)
    recent_1_hour_amount: Decimal = Field(ge=0)
    projected_1_hour_amount: Decimal = Field(gt=0)
    recent_incoming_amount: Decimal = Field(ge=0)
    reasons: list[str]
