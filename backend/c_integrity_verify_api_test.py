import hashlib
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


def fake_admin():
    return SimpleNamespace(id=1, role="ADMIN")


def override_db():
    yield fake_db


def test_hash(assessment):
    # 테스트 전용. 실제 기능에서는 B의 함수를 사용한다.
    value = (
        f"{assessment.id}|"
        f"{assessment.transaction_id}|"
        f"{assessment.final_risk_score}"
    )
    return hashlib.sha256(value.encode()).hexdigest()


def override_calculator():
    return test_hash


def run_tests():
    assessment = SimpleNamespace(
        id=1,
        transaction_id=25,
        final_risk_score=80.75,
    )

    query_result = (
        fake_db.query.return_value
        .filter.return_value
        .populate_existing.return_value
        .first
    )

    query_result.return_value = assessment

    record = {
        "exists": True,
        "transaction_id": 25,
        "digest": "0x" + test_hash(assessment),
    }

    app.dependency_overrides[require_admin] = fake_admin
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[
        get_analysis_hash_calculator
    ] = override_calculator

    try:
        with TestClient(app) as client:
            url = "/api/admin/analyses/1/integrity"

            with patch(
                "app.services.integrity_service.get_analysis_hash",
                return_value=record,
            ):
                response = client.get(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "MATCH"
                print("API_MATCH: PASS")

                assessment.final_risk_score = 10.0

                response = client.get(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "MISMATCH"
                print("API_MISMATCH: PASS")

                assessment.final_risk_score = 80.75

            with patch(
                "app.services.integrity_service.get_analysis_hash",
                return_value={"exists": False},
            ):
                response = client.get(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "NOT_RECORDED"
                print("API_NOT_RECORDED: PASS")

            query_result.return_value = None

            response = client.get(url)
            assert response.status_code == 404, response.text
            print("API_ANALYSIS_NOT_FOUND: PASS")

            query_result.return_value = assessment

            with patch(
                "app.services.integrity_service.get_analysis_hash",
                side_effect=BlockchainError("RPC unavailable"),
            ):
                response = client.get(url)
                assert response.status_code == 503, response.text
                print("API_RPC_ERROR: PASS")

            query_result.side_effect = SQLAlchemyError("DB unavailable")

            response = client.get(url)
            assert response.status_code == 503, response.text
            print("API_DB_ERROR: PASS")

            query_result.side_effect = None

            with patch(
                "app.services.integrity_service.get_analysis_hash",
                return_value=record,
            ):
                app.dependency_overrides[
                    get_analysis_hash_calculator
                ] = lambda: (lambda _: "invalid")

                response = client.get(url)
                assert response.status_code == 500, response.text
                print("API_INVALID_HASH: PASS")

            # B 함수가 연결되지 않은 실제 대기 상태 확인
            del app.dependency_overrides[
                get_analysis_hash_calculator
            ]

            response = client.get(url)
            assert response.status_code == 503, response.text
            assert "해시 함수 연결 대기" in response.json()["detail"]
            print("API_HASH_FUNCTION_PENDING: PASS")

        print("ALL_VERIFY_API_TESTS_PASSED")

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    run_tests()