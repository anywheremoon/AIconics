from enum import StrEnum

from sqlalchemy.orm import Session

from app.repositories import device_repository


class DeviceTrustStatus(StrEnum):
    TRUSTED_DEVICE = "TRUSTED_DEVICE"
    NEW_DEVICE = "NEW_DEVICE"
    SHARED_DEVICE = "SHARED_DEVICE"


def assess_device(
    db: Session, user_id: int, device_id: str
) -> DeviceTrustStatus:
    own_link = device_repository.find_user_link(db, device_id, user_id)
    linked_user_count = device_repository.count_users(db, device_id)

    if linked_user_count > (1 if own_link is not None else 0):
        return DeviceTrustStatus.SHARED_DEVICE
    if own_link is None:
        return DeviceTrustStatus.NEW_DEVICE
    return DeviceTrustStatus.TRUSTED_DEVICE


def record_device_use(db: Session, user_id: int, device_id: str):
    return device_repository.touch_device_and_link(db, device_id, user_id)