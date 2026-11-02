import json
import os
from pathlib import Path

from eth_account import Account
from web3 import Web3


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ABI_PATH = (
    PROJECT_ROOT / "blockchain" / "deployments" / "EthRiskVault.abi.json"
)


class EthVaultBlockchainError(RuntimeError):
    pass


def _configuration():
    rpc_url = os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
    chain_id = int(os.getenv("BLOCKCHAIN_CHAIN_ID", "31337"))
    address = os.getenv("ETH_VAULT_CONTRACT_ADDRESS", "")
    private_key = os.getenv("ETH_VAULT_SIGNER_PRIVATE_KEY", "")
    abi_path = Path(os.getenv("ETH_VAULT_ABI_PATH", str(DEFAULT_ABI_PATH)))
    if not Web3.is_address(address):
        raise EthVaultBlockchainError(
            "ETH_VAULT_CONTRACT_ADDRESS is not configured"
        )
    if not private_key:
        raise EthVaultBlockchainError(
            "ETH_VAULT_SIGNER_PRIVATE_KEY is not configured"
        )
    if not abi_path.is_file():
        raise EthVaultBlockchainError(
            "EthRiskVault ABI is unavailable; deploy the B component first"
        )
    return rpc_url, chain_id, address, private_key, abi_path


def _connect():
    rpc_url, chain_id, address, private_key, abi_path = _configuration()
    provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5})
    w3 = Web3(provider)
    if not w3.is_connected():
        raise EthVaultBlockchainError("ETH Vault blockchain is unavailable")
    if w3.eth.chain_id != chain_id:
        raise EthVaultBlockchainError(
            f"Expected chain ID {chain_id}, received {w3.eth.chain_id}"
        )
    checksum_address = Web3.to_checksum_address(address)
    if not w3.eth.get_code(checksum_address):
        raise EthVaultBlockchainError("EthRiskVault contract is not deployed")
    try:
        abi = json.loads(abi_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise EthVaultBlockchainError("Failed to load EthRiskVault ABI") from error
    return (
        w3,
        w3.eth.contract(address=checksum_address, abi=abi),
        Account.from_key(private_key),
        chain_id,
    )


def get_transfer(request_id: str):
    _, contract, _, _ = _connect()
    try:
        return contract.functions.getTransfer(request_id).call()
    except Exception as error:
        raise EthVaultBlockchainError("Failed to read ETH Vault transfer") from error


def submit_risk_result(signed_result: dict, signature: str) -> dict:
    w3, contract, account, chain_id = _connect()
    try:
        result_tuple = (
            signed_result["request_id"],
            signed_result["sender"],
            signed_result["recipient"],
            int(signed_result["amount"]),
            signed_result["risk_score"],
            signed_result["risk_level"],
            signed_result["requires_auth"],
            signed_result["requires_admin_approval"],
            signed_result["timelock_until"],
            signed_result["deadline"],
            signed_result["analysis_hash"],
            signed_result["nonce"],
        )
        transaction = contract.functions.submitRiskResult(
            result_tuple, signature
        ).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address, "pending"),
                "chainId": chain_id,
                "gasPrice": w3.eth.gas_price,
            }
        )
        transaction["gas"] = w3.eth.estimate_gas(transaction)
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        if receipt["status"] != 1:
            raise EthVaultBlockchainError("submitRiskResult transaction reverted")
        return {
            "transaction_hash": Web3.to_hex(tx_hash),
            "block_number": int(receipt["blockNumber"]),
        }
    except EthVaultBlockchainError:
        raise
    except Exception as error:
        raise EthVaultBlockchainError(
            "Failed to submit ETH Vault risk result"
        ) from error

