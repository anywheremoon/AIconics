import math


# Graph owns 20% of the final score.  The original 30:35:35 ratio across the
# other three domains is preserved inside the remaining 80%.
BEHAVIOR_WEIGHT = 0.24
IDENTITY_WEIGHT = 0.28
TRANSACTION_WEIGHT = 0.28
GRAPH_WEIGHT = 0.20

# Preserve the calibrated three-domain policy when Graph is unavailable.
LEGACY_BEHAVIOR_WEIGHT = 0.30
LEGACY_IDENTITY_WEIGHT = 0.35
LEGACY_TRANSACTION_WEIGHT = 0.35

# 현재 규칙에서 가능한 최대 합계
BEHAVIOR_RAW_MAX = 65.0
IDENTITY_RAW_MAX = 80.0


def validate_score(value, name: str) -> float:
    """유한한 0~100 범위의 점수인지 확인한다."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name}은 숫자여야 합니다.")

    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            f"{name}은 숫자여야 합니다."
        ) from error

    if not math.isfinite(score):
        raise ValueError(
            f"{name}은 유한한 숫자여야 합니다."
        )

    if not 0 <= score <= 100:
        raise ValueError(
            f"{name}은 0~100 범위여야 합니다."
        )

    return score


def normalize_rule_score(
    value,
    *,
    name: str,
    maximum: float,
) -> float:
    """현재 규칙의 원점수를 0~100 범위로 환산한다."""
    score = validate_score(value, name)

    if score > maximum:
        raise ValueError(
            f"{name}이 현재 규칙 최대점 {maximum}을 초과했습니다. "
            "규칙 또는 환산 기준이 변경되었는지 확인하세요."
        )

    return score / maximum * 100.0


def calculate_final_risk(
    *,
    behavior_score,
    identity_score,
    transaction_score,
    graph_score=None,
) -> dict:
    """
    거래 단계의 최종 위험 점수를 계산한다.

    입력:
    - behavior_score: 기존 엔진 원점수, 0~65
    - identity_score: 기존 엔진 원점수, 0~80
    - transaction_score: A가 제공하는 점수, 0~100
    """

    behavior_raw = validate_score(
        behavior_score,
        "behavior_score",
    )
    identity_raw = validate_score(
        identity_score,
        "identity_score",
    )
    transaction = validate_score(
        transaction_score,
        "transaction_score",
    )
    graph = (
        validate_score(graph_score, "graph_score")
        if graph_score is not None
        else None
    )

    behavior_normalized = normalize_rule_score(
        behavior_raw,
        name="behavior_score",
        maximum=BEHAVIOR_RAW_MAX,
    )

    identity_normalized = normalize_rule_score(
        identity_raw,
        name="identity_score",
        maximum=IDENTITY_RAW_MAX,
    )

    if graph is None:
        applied_weights = {
            "behavior": LEGACY_BEHAVIOR_WEIGHT,
            "identity": LEGACY_IDENTITY_WEIGHT,
            "transaction": LEGACY_TRANSACTION_WEIGHT,
            "graph": 0.0,
        }
    else:
        applied_weights = {
            "behavior": BEHAVIOR_WEIGHT,
            "identity": IDENTITY_WEIGHT,
            "transaction": TRANSACTION_WEIGHT,
            "graph": GRAPH_WEIGHT,
        }

    contributions = {
        "behavior": behavior_normalized * applied_weights["behavior"],
        "identity": identity_normalized * applied_weights["identity"],
        "transaction": transaction * applied_weights["transaction"],
        "graph": (graph or 0.0) * applied_weights["graph"],
    }

    final_score = max(
        0.0,
        min(100.0, sum(contributions.values())),
    )

    return {
        # 기존 엔진의 원점수
        "behavior_score": behavior_raw,
        "identity_score": identity_raw,
        "transaction_score": transaction,
        "graph_score": graph,

        # 거래 가중합에 사용한 환산 점수
        "normalized_behavior_score": behavior_normalized,
        "normalized_identity_score": identity_normalized,

        # 계산 기준도 함께 보존
        "normalization_maxima": {
            "behavior": BEHAVIOR_RAW_MAX,
            "identity": IDENTITY_RAW_MAX,
        },

        "weighted_contributions": contributions,
        "applied_weights": applied_weights,
        "final_risk_score": final_score,
    }
