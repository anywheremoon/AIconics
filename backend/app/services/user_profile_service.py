import ipaddress

from sqlalchemy.orm import Session

from app.repositories import user_profile_repository


def _to_subnet(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    try:
        address = ipaddress.ip_address(ip_address)
    except ValueError:
        return None
    prefix = 24 if address.version == 4 else 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


def create_initial_profile(
    db: Session,
    user_id: int,
    device_id: str,
    ip_address: str | None,
    location: str | None,
):
    return user_profile_repository.create_profile(
        db,
        {
            "user_id": user_id,
            "primary_device_id": device_id,
            "usual_ip_subnet": _to_subnet(ip_address),
            "usual_location": location,
            "event_count": 0,
        },
    )


def get_my_profile(db: Session, user_id: int):
    return user_profile_repository.find_by_user_id(db, user_id)


def update_profile_event_count(db: Session, user_id: int):
    profile = user_profile_repository.find_by_user_id(db, user_id)
    if profile is None:
        return None
    return user_profile_repository.update_event_count(db, user_id, profile.event_count + 1)
