import os
from dataclasses import dataclass
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from app.schemas.risk_transfer_schema import RiskTransferMessage


EIP712_DOMAIN_NAME = "AIconicsRiskTransfer"
EIP712_DOMAIN_VERSION = "1"
EIP712_PRIMARY_TYPE = "RiskTransfer"
SIGNER_PRIVATE_KEY_ENV = "AICONICS_TRANSFER_SIGNER_PRIVATE_KEY"

EIP712_DOMAIN_FIELDS = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]

RISK_TRANSFER_FIELDS = [
    {"name": "sender", "type": "address"},
    {"name": "recipient", "type": "address"},
    {"name": "amount", "type": "uint256"},
    {"name": "riskScore", "type": "uint8"},
    {"name": "riskLevel", "type": "uint8"},
    {"name": "requestId", "type": "bytes32"},
    {"name": "deadline", "type": "uint256"},
    {"name": "nonce", "type": "bytes32"},
]


class SignatureConfigurationError(RuntimeError):
    """Raised when the backend signer is absent or invalid."""


@dataclass(frozen=True)
class SignedTypedData:
    signer: str
    signature: str
    typed_data: dict[str, Any]


class TransferSignatureService:
    """Build and sign the exact EIP-712 payload consumed by RiskTransfer.sol."""

    def __init__(self, private_key: str | None = None):
        key = private_key or os.getenv(SIGNER_PRIVATE_KEY_ENV)
        if not key:
            raise SignatureConfigurationError(
                f"{SIGNER_PRIVATE_KEY_ENV} is not configured"
            )
        try:
            self._account = Account.from_key(key)
        except (TypeError, ValueError) as error:
            raise SignatureConfigurationError(
                f"{SIGNER_PRIVATE_KEY_ENV} is invalid"
            ) from error

    @property
    def signer_address(self) -> str:
        return self._account.address

    def build_typed_data(
        self,
        *,
        chain_id: int,
        verifying_contract: str,
        message: RiskTransferMessage,
    ) -> dict[str, Any]:
        return {
            "types": {
                "EIP712Domain": [dict(field) for field in EIP712_DOMAIN_FIELDS],
                EIP712_PRIMARY_TYPE: [dict(field) for field in RISK_TRANSFER_FIELDS],
            },
            "primaryType": EIP712_PRIMARY_TYPE,
            "domain": {
                "name": EIP712_DOMAIN_NAME,
                "version": EIP712_DOMAIN_VERSION,
                "chainId": chain_id,
                "verifyingContract": verifying_contract,
            },
            "message": message.model_dump(by_alias=True),
        }

    def sign(
        self,
        *,
        chain_id: int,
        verifying_contract: str,
        message: RiskTransferMessage,
    ) -> SignedTypedData:
        typed_data = self.build_typed_data(
            chain_id=chain_id,
            verifying_contract=verifying_contract,
            message=message,
        )
        signable = encode_typed_data(full_message=typed_data)
        signed = self._account.sign_message(signable)
        signature = signed.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature
        return SignedTypedData(
            signer=self.signer_address,
            signature=signature,
            typed_data=typed_data,
        )


def recover_typed_data_signer(typed_data: dict[str, Any], signature: str) -> str:
    """Recover a signer for tests, diagnostics, and integration validation."""
    signable = encode_typed_data(full_message=typed_data)
    return Account.recover_message(signable, signature=signature)
