from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.database import get_db
from app.routes.integrity import (
    get_analysis_hash_calculator,
    router,
)
from app.services.auth_service import get_current_user


app = FastAPI()
app.include_router(router)

fake_db = MagicMock()


def override_db():
    yield fake_db


def override_calculator():
    return lambda _: "0x" + "ab" * 32


def regular_user():
    return SimpleNamespace(id=2, role="USER")


def unauthenticated_user():
    raise HTTPException(
        status_code=401,
        detail="Not authenticated",
    )


def run_tests():
    endpoints = [
        ("GET", "/api/admin/analyses/1/chain-record"),
        ("GET", "/api/admin/analyses/1/integrity"),
        ("POST", "/api/admin/analyses/1/anchor"),
    ]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[
        get_analysis_hash_calculator
    ] = override_calculator

    try:
        with (
            TestClient(app) as client,
            patch(
                "app.routes.integrity.get_analysis_hash"
            ) as read_hash,
            patch(
                "app.routes.integrity.record_analysis_hash"
            ) as write_hash,
            patch(
                "app.routes.integrity.verify_analysis_integrity"
            ) as verify,
        ):
            # require_admin 자체는 대체하지 않는다.
            app.dependency_overrides[
                get_current_user
            ] = regular_user

            for method, url in endpoints:
                response = client.request(method, url)

                assert response.status_code == 403, (
                    method,
                    url,
                    response.status_code,
                    response.text,
                )

                print(f"USER_BLOCKED: {method} {url}: PASS")

            app.dependency_overrides[
                get_current_user
            ] = unauthenticated_user

            for method, url in endpoints:
                response = client.request(method, url)

                assert response.status_code == 401, (
                    method,
                    url,
                    response.status_code,
                    response.text,
                )

                print(f"UNAUTHENTICATED_BLOCKED: {method} {url}: PASS")

            read_hash.assert_not_called()
            write_hash.assert_not_called()
            verify.assert_not_called()
            fake_db.query.assert_not_called()

            print("NO_DB_OR_BLOCKCHAIN_ACCESS: PASS")

        print("ALL_PERMISSION_TESTS_PASSED")

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    run_tests()