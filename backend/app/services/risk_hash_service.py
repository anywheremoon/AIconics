
import hashlib
import json
import math

from app.models.risk_assessment_model import RiskAssessment


# C팀이 블록체인 검증에 사용할 해시 규칙
HASH_VERSION = "risk_assessment_sha256_v1"

HASH_FIELDS = (
    "transaction_id",
    "behavior_score",
    "identity_score",
    "transaction_score",
    "graph_score",
    "final_risk_score",
    "risk_level",
    "decision",
    "policy_version",
    "calculation_details",
)


def _normalize(value):
    """JSON 데이터를 일관된 형식으로 변환한다."""
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items())
        }

    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("유효하지 않은 위험 점수입니다.")
        return value

    if value is None or isinstance(value, (str, int, bool)):
        return value

    raise TypeError(
        f"지원하지 않는 데이터 형식: {type(value).__name__}"
    )


def serialize_risk_assessment(assessment: RiskAssessment) -> str:
    """위험 분석 결과를 동일한 JSON 형식으로 직렬화한다."""
    if not isinstance(assessment, RiskAssessment):
        raise TypeError("RiskAssessment 객체가 필요합니다.")

    data = {
        field: getattr(assessment, field)
        for field in HASH_FIELDS
    }

    payload = {
        "hash_version": HASH_VERSION,
        "assessment": _normalize(data),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def generate_risk_hash(assessment: RiskAssessment) -> str:
    """직렬화된 위험 분석 결과의 SHA-256 해시를 생성한다."""
    serialized = serialize_risk_assessment(assessment)

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()
