from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    request_id: UUID
    recipient_account_number: str = Field(pattern=r"^\d{12}$")
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class WithdrawRequest(BaseModel):
    request_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str
    transaction_type: str
    sender_account_id: int
    recipient_account_id: int | None
    sender_account_number: str | None = None
    recipient_account_number: str | None = None
    amount: Decimal
    status: str
    created_at: datetime
