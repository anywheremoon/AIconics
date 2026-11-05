from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
VaultStatus = Literal[
    "PENDING_ANALYSIS",
    "READY",
    "AUTH_REQUIRED",
    "ADMIN_REVIEW",
    "REJECTED",
    "RISK_SUBMITTED",
    "EXECUTED",
    "CANCELLED",
]

ADDRESS_PATTERN = r"^0x[0-9a-fA-F]{40}$"
BYTES32_PATTERN = r"^0x[0-9a-fA-F]{64}$"


class EthVaultAnalyzeRequest(BaseModel):
    request_id: str = Field(pattern=BYTES32_PATTERN)
    session_id: UUID
    sender_address: str = Field(pattern=ADDRESS_PATTERN)
    recipient_address: str = Field(pattern=ADDRESS_PATTERN)
    amount_wei: Decimal = Field(gt=0, max_digits=78, decimal_places=0)
    chain_id: int = Field(gt=0)
    verifying_contract: str = Field(pattern=ADDRESS_PATTERN)

    @field_validator("request_id")
    @classmethod
    def normalize_request_id(cls, value: str) -> str:
        return value.lower()

    @field_validator(
        "sender_address", "recipient_address", "verifying_contract"
    )
    @classmethod
    def normalize_address(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def reject_self_transfer(self):
        if self.sender_address.lower() == self.recipient_address.lower():
            raise ValueError("sender and recipient must be different")
        return self


class EthVaultPolicyResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    decision: str
    status: VaultStatus
    requires_auth: bool
    requires_admin_approval: bool
    timelock_seconds: int = Field(ge=0)


class EthVaultSignedResult(BaseModel):
    request_id: str = Field(pattern=BYTES32_PATTERN)
    sender: str = Field(pattern=ADDRESS_PATTERN)
    recipient: str = Field(pattern=ADDRESS_PATTERN)
    amount: str = Field(pattern=r"^[1-9][0-9]*$")
    risk_score: int = Field(ge=0, le=100)
    risk_level: int = Field(ge=0, le=3)
    requires_auth: bool
    requires_admin_approval: bool
    timelock_until: int = Field(ge=0)
    deadline: int = Field(gt=0)
    analysis_hash: str = Field(pattern=BYTES32_PATTERN)
    nonce: str = Field(pattern=BYTES32_PATTERN)


class EthVaultTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str
    user_id: int
    session_id: str
    sender_address: str
    recipient_address: str
    amount_wei: Decimal
    chain_id: int
    verifying_contract: str
    risk_score: int | None
    risk_level: RiskLevel | None
    decision: str | None
    status: VaultStatus
    requires_auth: bool
    requires_admin_approval: bool
    timelock_until: datetime | None
    signature_deadline: datetime | None
    analysis_hash: str | None
    nonce: str | None
    signature: str | None
    blockchain_tx_hash: str | None
    created_at: datetime
    updated_at: datetime


class EthVaultAnalyzeResponse(BaseModel):
    transfer: EthVaultTransferResponse
    policy: EthVaultPolicyResponse
    signed_result: EthVaultSignedResult
    signature: str = Field(pattern=r"^0x[0-9a-fA-F]{130}$")


class EthVaultSubmitResponse(BaseModel):
    request_id: str
    transaction_hash: str
    block_number: int
    status: VaultStatus

