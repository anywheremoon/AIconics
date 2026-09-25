import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user_model import User
from app.services.device_trust_service import (
    DeviceTrustStatus,
    assess_device,
    record_device_use,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def create_user(db, username):
    user = User(
        username=username,
        password_hash="test-password-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_new_device_becomes_trusted_after_use():
    db = TestingSessionLocal()

    user = create_user(db, "device-test-user")
    device_id = "device-test-001"

    # 처음 보는 기기
    first_status = assess_device(
        db,
        user.id,
        device_id,
    )

    assert first_status == DeviceTrustStatus.NEW_DEVICE

    # 로그인 성공 후 기기 사용 기록
    record_device_use(
        db,
        user.id,
        device_id,
    )
    db.commit()

    # 같은 사용자가 같은 기기를 다시 사용
    second_status = assess_device(
        db,
        user.id,
        device_id,
    )

    assert second_status == DeviceTrustStatus.TRUSTED_DEVICE

    db.close()

def test_device_becomes_shared_when_used_by_another_user():
    db = TestingSessionLocal()

    user1 = create_user(db, "device-user-1")
    user2 = create_user(db, "device-user-2")
    device_id = "shared-device-001"

    # 첫 번째 사용자가 기기 사용
    record_device_use(
        db,
        user1.id,
        device_id,
    )
    db.commit()

    # 두 번째 사용자가 같은 기기를 처음 사용
    status_before = assess_device(
        db,
        user2.id,
        device_id,
    )

    assert status_before == DeviceTrustStatus.SHARED_DEVICE

    db.close()