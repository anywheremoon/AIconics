import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from app.services.blockchain_service import BlockchainError
from app.services.integrity_service import verify_analysis_integrity


def test_hash(assessment):
    # 테스트 전용 규칙. B의 실제 해시 규칙을 대신하지 않는다.
    value = (
        f"{assessment.id}|"
        f"{assessment.transaction_id}|"
        f"{assessment.final_risk_score}"
    )
    return hashlib.sha256(value.encode()).hexdigest()


def run_tests():
    assessment = SimpleNamespace(
        id=1,
        transaction_id=25,
        final_risk_score=80.75,
    )

    original_hash = test_hash(assessment)

    record = {
        "exists": True,
        "transaction_id": 25,
        "digest": "0x" + original_hash,
    }

    with patch(
        "app.services.integrity_service.get_analysis_hash",
        return_value=record,
    ):
        result = verify_analysis_integrity(assessment, test_hash)
        assert result["status"] == "MATCH", result
        print("NORMAL_MATCH: PASS")

        # 메모리상의 테스트 객체만 변경한다. 실제 DB는 변경하지 않는다.
        assessment.final_risk_score = 10.0

        result = verify_analysis_integrity(assessment, test_hash)
        assert result["status"] == "MISMATCH", result
        print("SCORE_CHANGE_DETECTED: PASS")

        assessment.final_risk_score = 80.75
        assessment.transaction_id = 26

        # 해시가 같아도 거래 ID가 다르면 불일치여야 한다.
        result = verify_analysis_integrity(
            assessment,
            lambda _: original_hash,
        )
        assert result["status"] == "MISMATCH", result
        print("TRANSACTION_CHANGE_DETECTED: PASS")

        assessment.transaction_id = 25

        result = verify_analysis_integrity(
            assessment,
            lambda _: original_hash.upper(),
        )
        assert result["status"] == "MATCH", result
        print("HASH_FORMAT_NORMALIZED: PASS")

        try:
            verify_analysis_integrity(
                assessment,
                lambda _: "invalid",
            )
        except ValueError:
            print("INVALID_HASH_REJECTED: PASS")
        else:
            raise AssertionError("Invalid hash was accepted")

    with patch(
        "app.services.integrity_service.get_analysis_hash",
        return_value={"exists": False},
    ):
        def unexpected_hash_call(_):
            raise AssertionError("Hash calculation should not run")

        result = verify_analysis_integrity(
            assessment,
            unexpected_hash_call,
        )
        assert result["status"] == "NOT_RECORDED", result
        print("NOT_RECORDED: PASS")

    with patch(
        "app.services.integrity_service.get_analysis_hash",
        side_effect=BlockchainError("RPC unavailable"),
    ):
        try:
            verify_analysis_integrity(assessment, test_hash)
        except BlockchainError:
            print("RPC_ERROR_PROPAGATED: PASS")
        else:
            raise AssertionError("RPC error was hidden")

    print("ALL_INTEGRITY_SERVICE_TESTS_PASSED")


if __name__ == "__main__":
    run_tests()