from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.device_model import Device
from app.models.device_user_link_model import DeviceUserLink


def find_device(db: Session, device_id: str) -> Device | None:
    return db.query(Device).filter(Device.device_id == device_id).first()


def find_user_link(
    db: Session, device_id: str, user_id: int
) -> DeviceUserLink | None:
    return (
        db.query(DeviceUserLink)
        .filter(
            DeviceUserLink.device_id == device_id,
            DeviceUserLink.user_id == user_id,
        )
        .first()
    )


def count_users(db: Session, device_id: str) -> int:
    return int(
        db.query(func.count(DeviceUserLink.id))
        .filter(DeviceUserLink.device_id == device_id)
        .scalar()
        or 0
    )


def touch_device_and_link(
    db: Session, device_id: str, user_id: int
) -> DeviceUserLink:
    now = datetime.now(timezone.utc)
    device = find_device(db, device_id)
    if device is None:
        device = Device(device_id=device_id, first_seen=now, last_seen=now)
        db.add(device)
        db.flush()
    else:
        device.last_seen = now

    link = find_user_link(db, device_id, user_id)
    if link is None:
        link = DeviceUserLink(
            device_id=device_id,
            user_id=user_id,
            first_seen=now,
            last_seen=now,
        )
        db.add(link)
    else:
        link.last_seen = now

    db.flush()
    return link