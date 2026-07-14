from app.ml.services.anomaly_detector import anomaly_detector


def extract_ml_features(event_data: dict) -> list[float]:
    """
    API JSON에서 ML 모델 입력에 필요한 Feature를 추출한다.

    아래 순서는 모델 학습 시 사용한 컬럼 순서와
    반드시 같아야 한다.
    """

    required_features = [
        "typing_speed",
        "mouse_move_count",
        "click_count"
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

        except (TypeError, ValueError):
            raise ValueError(
                f"{feature_name} 값은 숫자여야 합니다."
            )

    return features


def detect_anomaly(event_data: dict) -> dict:
    """
    API 데이터를 Feature 배열로 변환한 뒤
    이상 탐지를 수행한다.
    """

    features = extract_ml_features(event_data)

    result = anomaly_detector.predict(features)

    return result