from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "datasets" / "merged_dataset.csv"
MODELS_DIR = BASE_DIR / "models"

MODEL_PATH = MODELS_DIR / "one_class_svm.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
FEATURES_PATH = MODELS_DIR / "feature_names.json"


# 학습에 사용할 Feature와 순서를 명시적으로 지정
# user, user_id 등의 식별자는 학습에 포함하지 않음
FEATURE_NAMES = [
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "total_keystrokes",
]


def load_training_data() -> tuple[pd.DataFrame, list[str]]:
    """CSV에서 지정한 Feature만 정해진 순서로 읽고 검증한다."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"데이터셋을 찾을 수 없습니다: {DATASET_PATH}"
        )

    if DATASET_PATH.stat().st_size == 0:
        raise ValueError("merged_dataset.csv가 비어 있습니다.")

    dataframe = pd.read_csv(DATASET_PATH)

    if dataframe.empty:
        raise ValueError("merged_dataset.csv에 학습 데이터가 없습니다.")

    # 필요한 Feature가 모두 있는지 확인
    missing_columns = [
        name
        for name in FEATURE_NAMES
        if name not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필수 Feature 컬럼이 없습니다: {missing_columns}"
        )

    # 지정한 컬럼만 지정한 순서대로 선택
    features = dataframe[FEATURE_NAMES].copy()

    # 숫자로 변환할 수 없는 값은 NaN으로 처리
    features = features.apply(pd.to_numeric, errors="coerce")

    # 결측치 또는 무한대가 있으면 학습을 중단
    invalid_values = (
        features.isna()
        | features.isin([float("inf"), float("-inf")])
    )

    if invalid_values.any().any():
        invalid_columns = features.columns[
            invalid_values.any()
        ].tolist()

        raise ValueError(
            "학습 데이터에 결측치, 숫자가 아닌 값 또는 무한대가 있습니다. "
            f"확인할 컬럼: {invalid_columns}"
        )

    if len(features) < 10:
        print(
            "경고: 학습 데이터가 10개 미만이라 "
            "모델 결과가 불안정할 수 있습니다."
        )

    return features, FEATURE_NAMES.copy()


def train_model() -> None:
    """StandardScaler와 One-Class SVM을 학습하고 저장한다."""
    features, feature_names = load_training_data()

    # Feature별 값의 크기를 표준화
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # One-Class SVM 학습
    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
    )
    model.fit(scaled_features)

    # 저장 폴더 생성
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 모델과 Scaler 저장
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    # 학습에 사용한 Feature 이름과 순서 저장
    with FEATURES_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            feature_names,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # 학습 데이터에 대한 예측 분포 확인
    # 별도 테스트 데이터의 성능 평가 결과는 아님
    predictions = model.predict(scaled_features)
    normal_count = int((predictions == 1).sum())
    anomaly_count = int((predictions == -1).sum())

    print("모델 학습 완료")
    print(f"학습 데이터 수: {len(features)}")
    print(f"사용 Feature: {feature_names}")
    print(f"학습 데이터 정상 예측 수: {normal_count}")
    print(f"학습 데이터 이상 예측 수: {anomaly_count}")
    print(f"모델 저장: {MODEL_PATH}")
    print(f"Scaler 저장: {SCALER_PATH}")
    print(f"Feature 목록 저장: {FEATURES_PATH}")


if __name__ == "__main__":
    train_model()