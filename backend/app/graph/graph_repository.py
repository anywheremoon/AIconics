from app.graph.graph_queries import (
    DETECT_COMMON_BENEFICIARY,
    DETECT_SHARED_DEVICE,
    DETECT_SHARED_DEVICE_COMMON_BENEFICIARY,
    DETECT_SHARED_IP_DEVICE,
    GET_TRANSACTION_GRAPH,
    MERGE_ACCOUNT,
    MERGE_DEVICE,
    MERGE_IP,
    MERGE_TRANSFER,
    MERGE_USER,
    MERGE_USER_ACCOUNT,
    MERGE_USER_DEVICE,
    MERGE_USER_IP,
    DELETE_USER,
    DELETE_USER_ACCOUNTS,
)
from app.graph.neo4j_client import driver


def _execute(query: str, **parameters):
    with driver.session() as session:
        return session.run(query, **parameters).consume()


def merge_user(user_id: int):
    return _execute(
        MERGE_USER,
        user_id=user_id,
    )


def merge_device(device_id: str):
    return _execute(
        MERGE_DEVICE,
        device_id=device_id,
    )


def merge_ip(ip_address: str):
    return _execute(
        MERGE_IP,
        ip_address=ip_address,
    )


def merge_account(
    account_id: int,
    account_number: str,
):
    return _execute(
        MERGE_ACCOUNT,
        account_id=account_id,
        account_number=account_number,
    )


def merge_user_device(
    user_id: int,
    device_id: str,
):
    return _execute(
        MERGE_USER_DEVICE,
        user_id=user_id,
        device_id=device_id,
    )


def merge_user_ip(
    user_id: int,
    ip_address: str,
):
    return _execute(
        MERGE_USER_IP,
        user_id=user_id,
        ip_address=ip_address,
    )


def merge_user_account(
    user_id: int,
    account_id: int,
    account_number: str,
):
    return _execute(
        MERGE_USER_ACCOUNT,
        user_id=user_id,
        account_id=account_id,
        account_number=account_number,
    )


def merge_transfer(
    transaction_id: int,
    sender_account_id: int,
    recipient_account_id: int,
    amount: float,
    created_at,
):
    return _execute(
        MERGE_TRANSFER,
        transaction_id=transaction_id,
        sender_account_id=sender_account_id,
        recipient_account_id=recipient_account_id,
        amount=amount,
        created_at=created_at,
    )

def detect_shared_device(user_id: int) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            DETECT_SHARED_DEVICE,
            user_id=user_id,
        )
        return [dict(record) for record in result]

def detect_shared_ip_device(user_id: int) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            DETECT_SHARED_IP_DEVICE,
            user_id=user_id,
        )
        return [dict(record) for record in result]

def detect_common_beneficiary(user_id: int) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            DETECT_COMMON_BENEFICIARY,
            user_id=user_id,
        )
        return [dict(record) for record in result]

def detect_shared_device_common_beneficiary(user_id: int) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            DETECT_SHARED_DEVICE_COMMON_BENEFICIARY,
            user_id=user_id,
        )
        return [dict(record) for record in result]

def get_transaction_graph(transaction_id: int) -> dict | None:
    with driver.session() as session:
        record = session.run(
            GET_TRANSACTION_GRAPH,
            transaction_id=transaction_id,
        ).single()

        if record is None:
            return None

        data = dict(record)

        if data["created_at"] is not None:
           data["created_at"] = data["created_at"].iso_format()

        return data

def delete_user_graph(user_id: int):
    _execute(
        DELETE_USER_ACCOUNTS,
        user_id=user_id,
    )

    return _execute(
        DELETE_USER,
        user_id=user_id,
    )