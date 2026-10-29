import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevelName = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

ETHEREUM_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
ZERO_ADDRESS = "0x" + "0" * 40
UINT256_MAX = 2**256 - 1


class RiskTransferRequest(BaseModel):
    """Unsigned blockchain transfer submitted for risk assessment."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sender: str
    recipient: str
    amount: str
    chain_id: Annotated[int, Field(alias="chainId", gt=0, le=UINT256_MAX)]
    verifying_contract: str = Field(alias="verifyingContract")
    deadline: Annotated[int | None, Field(gt=0, le=UINT256_MAX)] = None

    @field_validator("sender", "recipient", "verifying_contract")
    @classmethod
    def validate_ethereum_address(cls, value: str) -> str:
        if not ETHEREUM_ADDRESS_PATTERN.fullmatch(value):
            raise ValueError("must be a 20-byte 0x-prefixed Ethereum address")
        # Address equality and signature hashing are case-insensitive. Returning
        # lower case also gives all three teams one canonical JSON representation.
        normalized = value.lower()
        if normalized == ZERO_ADDRESS:
            raise ValueError("must not be the zero address")
        return normalized

    @field_validator("recipient")
    @classmethod
    def recipient_must_differ_from_sender(cls, value: str, info) -> str:
        sender = info.data.get("sender")
        if sender is not None and value == sender:
            raise ValueError("recipient must differ from sender")
        return value

    @field_validator("amount")
    @classmethod
    def validate_base_unit_amount(cls, value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
            raise ValueError("must be a positive base-unit integer string")
        if int(value) > UINT256_MAX:
            raise ValueError("must fit in uint256")
        return value


class RiskTransferMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sender: str
    recipient: str
    amount: str
    risk_score: Annotated[int, Field(alias="riskScore", ge=0, le=100)]
    risk_level: Annotated[int, Field(alias="riskLevel", ge=0, le=3)]
    request_id: str = Field(alias="requestId", pattern=r"^0x[0-9a-f]{64}$")
    deadline: Annotated[int, Field(gt=0, le=UINT256_MAX)]
    nonce: str = Field(pattern=r"^0x[0-9a-f]{64}$")


class EIP712Domain(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    version: str
    chain_id: int = Field(alias="chainId")
    verifying_contract: str = Field(alias="verifyingContract")


class EIP712Field(BaseModel):
    name: str
    type: str


class EIP712TypedData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    domain: EIP712Domain
    types: dict[str, list[EIP712Field]]
    primary_type: str = Field(alias="primaryType")
    message: RiskTransferMessage


class RiskTransferResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    risk_score: int = Field(alias="riskScore", ge=0, le=100)
    risk_level: RiskLevelName = Field(alias="riskLevel")
    risk_level_code: int = Field(alias="riskLevelCode", ge=0, le=3)
    request_id: str = Field(alias="requestId", pattern=r"^0x[0-9a-f]{64}$")
    nonce: str = Field(pattern=r"^0x[0-9a-f]{64}$")
    deadline: int
    signer: str
    signature: str = Field(pattern=r"^0x[0-9a-f]{130}$")
    typed_data: EIP712TypedData = Field(alias="typedData")
