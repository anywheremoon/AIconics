import math

from app.ml.services.anomaly_detector import anomaly_detector


# train_model.py의 FEATURE_NAMES와 동일한 순서
REQUIRED_FEATURES = [
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "total_keystrokes",
]


def extract_ml_features(event_data: dict) -> list[float]:
    """API 데이터에서 실제 측정값을 정해진 순서로 추출한다."""

    features = []

    for feature_name in REQUIRED_FEATURES:
        value = event_data.get(feature_name)

        if value is None:
            raise ValueError(
                f"필수 Feature가 없습니다: {feature_name}"
            )

        if isinstance(value, bool):
            raise ValueError(
                f"{feature_name} 값은 불리언이 아닌 숫자여야 합니다."
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"{feature_name} 값은 숫자여야 합니다."
            ) from error

        if not math.isfinite(numeric_value):
            raise ValueError(
                f"{feature_name} 값은 유한한 숫자여야 합니다."
            )

        if numeric_value < 0:
            raise ValueError(
                f"{feature_name} 값은 0 이상이어야 합니다."
            )

        if (
            feature_name == "total_keystrokes"
            and not numeric_value.is_integer()
        ):
            raise ValueError(
                "total_keystrokes 값은 정수여야 합니다."
            )

        features.append(numeric_value)

    return features


def detect_anomaly(event_data: dict) -> dict:
    """API 데이터를 모델 입력으로 변환하고 이상 탐지를 수행한다."""

    features = extract_ml_features(event_data)

    return anomaly_detector.predict(features)