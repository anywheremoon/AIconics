from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.routes.integrity import (
    get_analysis_hash_calculator,
    router,
)
from app.services.blockchain_service import BlockchainError


app = FastAPI()
app.include_router(router)

fake_db = MagicMock()
digest = "0x" + "ab" * 32

assessment = SimpleNamespace(
    id=1,
    transaction_id=25,
)


def fake_admin():
    return SimpleNamespace(id=1, role="ADMIN")


def override_db():
    yield fake_db


def override_calculator():
    # 테스트 전용 해시. 실제 기능은 B의 함수를 사용한다.
    return lambda _: digest


def run_tests():
    query_result = (
        fake_db.query.return_value
        .filter.return_value
        .populate_existing.return_value
        .with_for_update.return_value
        .first
    )
    query_result.return_value = assessment

    app.dependency_overrides[require_admin] = fake_admin
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[
        get_analysis_hash_calculator
    ] = override_calculator

    try:
        with TestClient(app) as client:
            url = "/api/admin/analyses/1/anchor"

            with (
                patch(
                    "app.routes.integrity.get_analysis_hash"
                ) as read_hash,
                patch(
                    "app.routes.integrity.record_analysis_hash"
                ) as write_hash,
            ):
                read_hash.return_value = {"exists": False}
                write_hash.return_value = {
                    "analysis_id": 1,
                    "transaction_id": 25,
                    "digest": digest,
                    "tx_hash": "0x" + "cd" * 32,
                    "block_number": 10,
                }

                response = client.post(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "RECORDED"
                write_hash.assert_called_once_with(1, 25, digest)
                print("FIRST_RECORD: PASS")

                write_hash.reset_mock()

                read_hash.return_value = {
                    "exists": True,
                    "transaction_id": 25,
                    "digest": digest,
                }

                response = client.post(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "ALREADY_RECORDED"
                write_hash.assert_not_called()
                print("SAME_DATA_NO_DUPLICATE: PASS")

                read_hash.return_value = {
                    "exists": True,
                    "transaction_id": 25,
                    "digest": "0x" + "ef" * 32,
                }

                response = client.post(url)
                assert response.status_code == 409, response.text
                write_hash.assert_not_called()
                print("HASH_CHANGE_BLOCKED: PASS")

                read_hash.return_value = {
                    "exists": True,
                    "transaction_id": 26,
                    "digest": digest,
                }

                response = client.post(url)
                assert response.status_code == 409, response.text
                write_hash.assert_not_called()
                print("TRANSACTION_CHANGE_BLOCKED: PASS")

                query_result.return_value = None
                read_hash.reset_mock()

                response = client.post(url)
                assert response.status_code == 404, response.text
                read_hash.assert_not_called()
                write_hash.assert_not_called()
                print("ANALYSIS_NOT_FOUND: PASS")

                query_result.return_value = assessment

                read_hash.side_effect = BlockchainError("RPC unavailable")

                response = client.post(url)
                assert response.status_code == 503, response.text
                write_hash.assert_not_called()
                print("READ_ERROR_NO_WRITE: PASS")

                read_hash.side_effect = None
                read_hash.return_value = {"exists": False}
                write_hash.side_effect = BlockchainError(
                    "Confirmation timeout"
                )

                response = client.post(url)
                assert response.status_code == 503, response.text
                print("WRITE_ERROR: PASS")

                write_hash.reset_mock()
                write_hash.side_effect = None
                read_hash.reset_mock()

                query_result.side_effect = SQLAlchemyError(
                    "DB unavailable"
                )

                response = client.post(url)
                assert response.status_code == 503, response.text
                read_hash.assert_not_called()
                write_hash.assert_not_called()
                print("DB_ERROR_NO_WRITE: PASS")

                query_result.side_effect = None

                for invalid_digest in ("invalid", "0x" + "00" * 32):
                    app.dependency_overrides[
                        get_analysis_hash_calculator
                    ] = lambda value=invalid_digest: (
                        lambda _: value
                    )

                    response = client.post(url)
                    assert response.status_code == 500, response.text

                read_hash.assert_not_called()
                write_hash.assert_not_called()
                print("INVALID_HASH_NO_WRITE: PASS")

                del app.dependency_overrides[
                    get_analysis_hash_calculator
                ]

                response = client.post(url)
                assert response.status_code == 503, response.text
                assert "해시 함수 연결 대기" in response.json()["detail"]
                write_hash.assert_not_called()
                print("HASH_FUNCTION_PENDING: PASS")

        print("ALL_ANCHOR_API_TESTS_PASSED")

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    run_tests()