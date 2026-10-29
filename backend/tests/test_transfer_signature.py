from copy import deepcopy

from eth_account import Account

from app.schemas.risk_transfer_schema import RiskTransferMessage
from app.services.transfer_signature_service import (
    EIP712_DOMAIN_NAME,
    EIP712_DOMAIN_VERSION,
    EIP712_PRIMARY_TYPE,
    RISK_TRANSFER_FIELDS,
    TransferSignatureService,
    recover_typed_data_signer,
)


PRIVATE_KEY = "0x" + "11" * 32
SENDER = "0x" + "22" * 20
RECIPIENT = "0x" + "33" * 20
CONTRACT = "0x" + "44" * 20


def transfer_message() -> RiskTransferMessage:
    return RiskTransferMessage(
        sender=SENDER,
        recipient=RECIPIENT,
        amount="1000000000000000000",
        riskScore=25,
        riskLevel=0,
        requestId="0x" + "55" * 32,
        deadline=1_790_000_000,
        nonce="0x" + "66" * 32,
    )


def test_signs_and_recovers_exact_eip712_payload():
    service = TransferSignatureService(PRIVATE_KEY)
    signed = service.sign(
        chain_id=31337,
        verifying_contract=CONTRACT,
        message=transfer_message(),
    )

    assert signed.signer == Account.from_key(PRIVATE_KEY).address
    assert recover_typed_data_signer(
        signed.typed_data, signed.signature
    ) == signed.signer
    assert signed.typed_data["domain"] == {
        "name": EIP712_DOMAIN_NAME,
        "version": EIP712_DOMAIN_VERSION,
        "chainId": 31337,
        "verifyingContract": CONTRACT,
    }
    assert signed.typed_data["primaryType"] == EIP712_PRIMARY_TYPE
    assert signed.typed_data["types"][EIP712_PRIMARY_TYPE] == RISK_TRANSFER_FIELDS
    assert list(signed.typed_data["message"]) == [
        "sender",
        "recipient",
        "amount",
        "riskScore",
        "riskLevel",
        "requestId",
        "deadline",
        "nonce",
    ]


def test_signature_is_bound_to_every_transfer_value():
    service = TransferSignatureService(PRIVATE_KEY)
    signed = service.sign(
        chain_id=31337,
        verifying_contract=CONTRACT,
        message=transfer_message(),
    )
    tampered = deepcopy(signed.typed_data)
    tampered["message"]["amount"] = "1000000000000000001"

    assert recover_typed_data_signer(tampered, signed.signature) != signed.signer


def test_domain_separates_chain_and_contract():
    service = TransferSignatureService(PRIVATE_KEY)
    signed = service.sign(
        chain_id=31337,
        verifying_contract=CONTRACT,
        message=transfer_message(),
    )
    wrong_chain = deepcopy(signed.typed_data)
    wrong_chain["domain"]["chainId"] = 1
    wrong_contract = deepcopy(signed.typed_data)
    wrong_contract["domain"]["verifyingContract"] = "0x" + "77" * 20

    assert recover_typed_data_signer(wrong_chain, signed.signature) != signed.signer
    assert recover_typed_data_signer(wrong_contract, signed.signature) != signed.signer
