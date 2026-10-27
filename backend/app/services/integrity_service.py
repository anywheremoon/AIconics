from app.services.blockchain_service import get_analysis_hash


def normalize_digest(value):
    """0x 유무와 영문 대소문자를 통일한다."""
    if not isinstance(value, str):
        raise ValueError("Hash must be a hexadecimal string")

    value = value.removeprefix("0x").removeprefix("0X")

    if len(value) != 64:
        raise ValueError("Hash must contain 64 hexadecimal characters")

    if any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("Hash contains invalid characters")

    return "0x" + value.lower()


def verify_analysis_integrity(assessment, calculate_hash):
    """
    assessment: DB에서 새로 조회한 RiskAssessment
    calculate_hash: B가 제공할 분석 결과 해시 계산 함수

    블록체인 연결 오류와 해시 계산 오류는 호출 측으로 전달한다.
    오류를 정상 또는 데이터 변경으로 판정하지 않는다.
    """
    record = get_analysis_hash(assessment.id)

    if not record["exists"]:
        return {
            "analysis_id": assessment.id,
            "transaction_id": assessment.transaction_id,
            "status": "NOT_RECORDED",
            "message": "블록체인 기록이 없습니다.",
            "current_hash": None,
            "chain_hash": None,
        }

    # 저장해 둔 해시를 읽는 대신 현재 분석 필드에서 재계산한다.
    current_hash = normalize_digest(calculate_hash(assessment))
    chain_hash = normalize_digest(record["digest"])

    transaction_matches = (
        record["transaction_id"] == assessment.transaction_id
    )
    hash_matches = current_hash == chain_hash

    matches = transaction_matches and hash_matches

    return {
        "analysis_id": assessment.id,
        "transaction_id": assessment.transaction_id,
        "status": "MATCH" if matches else "MISMATCH",
        "message": "정상" if matches else "데이터 변경 탐지",
        "current_hash": current_hash,
        "chain_hash": chain_hash,
    }