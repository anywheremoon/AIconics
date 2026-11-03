"""Local development blockchain integration."""

import json
from pathlib import Path

from web3 import Web3


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEPLOYMENT_DIR = PROJECT_ROOT / "blockchain" / "deployments"


class BlockchainError(RuntimeError):
    """Blockchain connection, configuration or contract operation failed."""


def _connect():
    try:
        deployment = json.loads(
            (DEPLOYMENT_DIR / "localhost.json").read_text(
                encoding="utf-8-sig"
            )
        )
        abi = json.loads(
            (DEPLOYMENT_DIR / "AnalysisRegistry.abi.json").read_text(
                encoding="utf-8-sig"
            )
        )

        # This service intentionally supports only the local test node.
        rpc_url = "http://127.0.0.1:8545"

        w3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": 5},
            )
        )

        if not w3.is_connected():
            raise BlockchainError("Local blockchain is unavailable")

        if w3.eth.chain_id != 31337:
            raise BlockchainError("Expected local chain ID 31337")

        if deployment["chain_id"] != 31337:
            raise BlockchainError("Invalid deployment chain ID")

        address = Web3.to_checksum_address(
            deployment["contract_address"]
        )

        if not w3.eth.get_code(address):
            raise BlockchainError(
                "Contract not found. Redeploy after restarting the node."
            )

        contract = w3.eth.contract(address=address, abi=abi)

        owner = Web3.to_checksum_address(
            deployment["owner_address"]
        )

        if contract.functions.owner().call() != owner:
            raise BlockchainError("Contract owner does not match deployment")

        return w3, contract, owner

    except BlockchainError:
        raise
    except Exception as exc:
        raise BlockchainError(
            "Failed to load deployment or connect to blockchain"
        ) from exc


def _validate_id(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value >= 2**256
    ):
        raise ValueError(f"{name} must be a positive uint256 integer")


def _parse_digest(digest):
    if not isinstance(digest, str):
        raise ValueError("digest must be a hexadecimal string")

    value = digest[2:] if digest.startswith("0x") else digest

    if len(value) != 64:
        raise ValueError("digest must contain exactly 64 hexadecimal characters")

    if any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("digest contains invalid hexadecimal characters")

    raw = bytes.fromhex(value)

    if raw == bytes(32):
        raise ValueError("digest must not be zero")

    return raw


def get_analysis_hash(analysis_id):
    """Return a chain record; connection errors are never treated as missing."""
    _validate_id(analysis_id, "analysis_id")
    _, contract, _ = _connect()

    try:
        exists, transaction_id, digest, recorded_at = (
            contract.functions.getAnalysis(analysis_id).call()
        )

        return {
            "exists": bool(exists),
            "analysis_id": analysis_id,
            "transaction_id": int(transaction_id),
            "digest": Web3.to_hex(digest) if exists else None,
            "recorded_at": int(recorded_at) if exists else None,
        }
    except Exception as exc:
        raise BlockchainError("Failed to read analysis hash") from exc


def record_analysis_hash(analysis_id, transaction_id, digest):
    """Record using the local node's unlocked deployment account."""
    _validate_id(analysis_id, "analysis_id")
    _validate_id(transaction_id, "transaction_id")
    raw_digest = _parse_digest(digest)

    w3, contract, owner = _connect()

    try:
        tx_hash = contract.functions.recordAnalysis(
            analysis_id,
            transaction_id,
            raw_digest,
        ).transact({"from": owner})

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=30,
        )

        if receipt["status"] != 1:
            raise BlockchainError("Blockchain transaction failed")

        return {
            "analysis_id": analysis_id,
            "transaction_id": transaction_id,
            "digest": Web3.to_hex(raw_digest),
            "tx_hash": Web3.to_hex(tx_hash),
            "block_number": int(receipt["blockNumber"]),
        }
    except BlockchainError:
        raise
    except Exception as exc:
        raise BlockchainError(
            "Record failed or confirmation was not received. "
            "Check the chain record before retrying."
        ) from exc