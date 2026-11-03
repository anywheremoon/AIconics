from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.auth_dependency import require_admin
from app.routes.integrity import router
from app.services.blockchain_service import BlockchainError


# 실제 서버와 별개의 테스트용 앱.
# main.py를 불러오지 않으므로 DB 시작 작업도 실행하지 않는다.
app = FastAPI()
app.include_router(router)


def fake_admin():
    return SimpleNamespace(id=1, role="ADMIN")


# 테스트 앱에서만 인증 대체
app.dependency_overrides[require_admin] = fake_admin


def run_tests():
    try:
        with TestClient(app) as client:
            missing_record = {
                "exists": False,
                "analysis_id": 1,
                "transaction_id": 0,
                "digest": None,
                "recorded_at": None,
            }

            with patch(
                "app.routes.integrity.get_analysis_hash",
                return_value=missing_record,
            ) as mocked:
                response = client.get(
                    "/api/admin/analyses/1/chain-record"
                )

                assert response.status_code == 200, response.text
                body = response.json()
                assert body["status"] == "NOT_RECORDED", body
                assert body["digest"] is None, body
                mocked.assert_called_once_with(1)

            print("NOT_RECORDED_RESPONSE: PASS")

            existing_record = {
                "exists": True,
                "analysis_id": 1,
                "transaction_id": 25,
                "digest": "0x" + "ab" * 32,
                "recorded_at": 1700000000,
            }

            with patch(
                "app.routes.integrity.get_analysis_hash",
                return_value=existing_record,
            ):
                response = client.get(
                    "/api/admin/analyses/1/chain-record"
                )

                assert response.status_code == 200, response.text
                body = response.json()
                assert body["status"] == "RECORDED", body
                assert body["transaction_id"] == 25, body
                assert body["digest"] == existing_record["digest"], body

            print("RECORDED_RESPONSE: PASS")

            with patch(
                "app.routes.integrity.get_analysis_hash",
                side_effect=BlockchainError("RPC unavailable"),
            ):
                response = client.get(
                    "/api/admin/analyses/1/chain-record"
                )

                assert response.status_code == 503, response.text
                body = response.json()
                assert "detail" in body, body
                assert "status" not in body, body

            print("RPC_ERROR_RESPONSE: PASS")

            with patch(
                "app.routes.integrity.get_analysis_hash"
            ) as mocked:
                for invalid_id in ("0", "-1", "abc"):
                    response = client.get(
                        f"/api/admin/analyses/{invalid_id}/chain-record"
                    )
                    assert response.status_code == 422, response.text

                mocked.assert_not_called()

            print("INVALID_ID_REJECTED: PASS")

        print("ALL_ROUTE_TESTS_PASSED")

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    run_tests()