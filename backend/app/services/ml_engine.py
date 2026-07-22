from app.ml.services.anomaly_detector import anomaly_detector


def extract_ml_features(event_data: dict) -> list[float]:
    """
    API JSON에서 ML 모델 입력 Feature를 추출한다.

    이 순서는 merged_dataset.csv와 모델 학습 순서와
    반드시 동일해야 한다.
    """

    required_features = [
        "typing_speed",
        "avg_hold_time",
        "avg_flight_time",
        "total_keystrokes"
    ]

    features = []

    for feature_name in required_features:
        value = event_data.get(feature_name)

        if value is None:
            raise ValueError(
                f"필수 Feature가 없습니다: {feature_name}"
            )

        try:
            features.append(float(value))

        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{feature_name} 값은 숫자여야 합니다."
            ) from error

    return features


def detect_anomaly(event_data: dict) -> dict:
    """
    API 데이터를 모델 입력 형태로 변환하고 이상 탐지를 수행한다.
    """

    features = extract_ml_features(event_data)

    return anomaly_detector.predict(features)