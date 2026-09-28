import logging

from app.graph.graph_repository import (
    merge_transfer,
    merge_user_account,
    merge_user_device,
    merge_user_ip,
)


logger = logging.getLogger(__name__)


def sync_transfer(transaction, sender, recipient) -> bool:
    try:
        merge_user_account(
            sender.user_id,
            sender.id,
            sender.account_number,
        )

        merge_user_account(
            recipient.user_id,
            recipient.id,
            recipient.account_number,
        )

        merge_transfer(
            transaction.id,
            sender.id,
            recipient.id,
            float(transaction.amount),
            transaction.created_at,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to sync transaction %s to Neo4j",
            transaction.id,
        )
        return False

def sync_login(
    user_id: int,
    device_id: str | None,
    ip_address: str | None,
) -> bool:
    try:
        if device_id:
            merge_user_device(user_id, device_id)

        if ip_address:
            merge_user_ip(user_id, ip_address)

        return True

    except Exception:
        logger.exception(
            "Failed to sync login for user %s to Neo4j",
            user_id,
        )
        return False

def sync_registration(user, account) -> bool:
    try:
        merge_user_account(
            user.id,
            account.id,
            account.account_number,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to sync registration for user %s to Neo4j",
            user.id,
        )
        return False