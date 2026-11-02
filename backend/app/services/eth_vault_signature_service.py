import json
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3


DOMAIN_NAME = "AIconics EthRiskVault"
DOMAIN_VERSION = "1"
RISK_LEVEL_CODES = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

RISK_RESULT_FIELDS = [
    {"name": "requestId", "type": "bytes32"},
    {"name": "sender", "type": "address"},
    {"name": "recipient", "type": "address"},
    {"name": "amount", "type": "uint256"},
    {"name": "riskScore", "type": "uint256"},
    {"name": "riskLevel", "type": "uint8"},
    {"name": "requiresAuth", "type": "bool"},
    {"name": "requiresAdminApproval", "type": "bool"},
    {"name": "timelockUntil", "type": "uint256"},
    {"name": "deadline", "type": "uint256"},
    {"name": "analysisHash", "type": "bytes32"},
    {"name": "nonce", "type": "bytes32"},
]


class EthVaultSigningError(RuntimeError):
    pass


def _unix_time(value: datetime | None) -> int:
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def new_nonce() -> str:
    return "0x" + secrets.token_hex(32)


def build_analysis_hash(
    *,
    request_id: str,
    risk_score: int,
    risk_level: str,
    decision: str,
    reasons: list[dict],
) -> str:
    canonical = json.dumps(
        {
            "requestId": request_id.lower(),
            "riskScore": int(risk_score),
            "riskLevel": risk_level,
            "decision": decision,
            "reasons": reasons,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return Web3.to_hex(Web3.keccak(canonical))


def build_signed_result(
    *,
    request_id: str,
    sender_address: str,
    recipient_address: str,
    amount_wei: Decimal | int | str,
    risk_score: int,
    risk_level: str,
    requires_auth: bool,
    requires_admin_approval: bool,
    timelock_until: datetime | None,
    deadline: datetime,
    analysis_hash: str,
    nonce: str,
) -> dict:
    return {
        "request_id": request_id.lower(),
        "sender": Web3.to_checksum_address(sender_address),
        "recipient": Web3.to_checksum_address(recipient_address),
        "amount": str(int(amount_wei)),
        "risk_score": int(risk_score),
        "risk_level": RISK_LEVEL_CODES[risk_level],
        "requires_auth": bool(requires_auth),
        "requires_admin_approval": bool(requires_admin_approval),
        "timelock_until": _unix_time(timelock_until),
        "deadline": _unix_time(deadline),
        "analysis_hash": analysis_hash.lower(),
        "nonce": nonce.lower(),
    }


def typed_data(
    result: dict,
    *,
    chain_id: int,
    verifying_contract: str,
) -> dict:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "RiskResult": RISK_RESULT_FIELDS,
        },
        "primaryType": "RiskResult",
        "domain": {
            "name": DOMAIN_NAME,
            "version": DOMAIN_VERSION,
            "chainId": int(chain_id),
            "verifyingContract": Web3.to_checksum_address(verifying_contract),
        },
        "message": {
            "requestId": result["request_id"],
            "sender": result["sender"],
            "recipient": result["recipient"],
            "amount": int(result["amount"]),
            "riskScore": result["risk_score"],
            "riskLevel": result["risk_level"],
            "requiresAuth": result["requires_auth"],
            "requiresAdminApproval": result["requires_admin_approval"],
            "timelockUntil": result["timelock_until"],
            "deadline": result["deadline"],
            "analysisHash": result["analysis_hash"],
            "nonce": result["nonce"],
        },
    }


def sign_result(
    result: dict,
    *,
    chain_id: int,
    verifying_contract: str,
    private_key: str | None = None,
) -> str:
    key = private_key or os.getenv("ETH_VAULT_SIGNER_PRIVATE_KEY")
    if not key:
        raise EthVaultSigningError(
            "ETH_VAULT_SIGNER_PRIVATE_KEY is not configured"
        )
    try:
        message = encode_typed_data(
            full_message=typed_data(
                result,
                chain_id=chain_id,
                verifying_contract=verifying_contract,
            )
        )
        return Web3.to_hex(
            Account.sign_message(message, private_key=key).signature
        )
    except Exception as error:
        raise EthVaultSigningError("Failed to sign ETH Vault risk result") from error


def recover_signer(
    result: dict,
    signature: str,
    *,
    chain_id: int,
    verifying_contract: str,
) -> str:
    message = encode_typed_data(
        full_message=typed_data(
            result,
            chain_id=chain_id,
            verifying_contract=verifying_contract,
        )
    )
    return Account.recover_message(message, signature=signature)

