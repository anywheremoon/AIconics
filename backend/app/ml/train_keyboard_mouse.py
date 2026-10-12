from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM


BASE_DIR = Path(__file__).resolve().parent

# AIconics 프로젝트 최상위 폴더
PROJECT_DIR = BASE_DIR.parents[2]

DATASET_PATH = (
    PROJECT_DIR
    / "agent"
    / "datasets"
    / "keyboard_mouse_dataset.csv"
)

# 기존 키보드 모델과 분리해서 저장
MODELS_DIR = BASE_DIR / "models" / "keyboard_mouse"

MODEL_PATH = MODELS_DIR / "one_class_svm.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
FEATURES_PATH = MODELS_DIR / "feature_names.json"
METADATA_PATH = MODELS_DIR / "training_metadata.json"


FEATURE_NAMES = [
    "typing_speed",
    "avg_hold_time",
    "avg_flight_time",
    "total_keystrokes",
    "mouse_move_count",
    "mouse_move_distance",
    "click_count",
]

COUNT_FEATURES = [
    "total_keystrokes",
    "mouse_move_count",
    "click_count",
]

EXPECTED_DURATION_SECONDS = 30

# 시험 학습을 위한 임시 최소 개수
# 탐지 성능을 보장하는 기준은 아님
MIN_TRAINING_SAMPLES = 30


def load_training_data():
    """Agent가 저장한 키보드·마우스 데이터를 읽고 검증한다."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"학습 CSV가 없습니다: {DATASET_PATH}"
        )

    if DATASET_PATH.stat().st_size == 0:
        raise ValueError("학습 CSV가 비어 있습니다.")

    dataframe = pd.read_csv(DATASET_PATH)

    if dataframe.empty:
        raise ValueError("학습 CSV에 데이터가 없습니다.")

    required_columns = [
        "collection_duration_seconds",
        *FEATURE_NAMES,
    ]

    missing_columns = [
        name
        for name in required_columns
        if name not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필수 컬럼이 없습니다: {missing_columns}"
        )

    numeric_data = dataframe[required_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )

    invalid_values = ~np.isfinite(
        numeric_data.to_numpy(dtype=float)
    )

    if invalid_values.any():
        raise ValueError(
            "CSV에 결측치, 숫자가 아닌 값 또는 무한대가 있습니다."
        )

    if (numeric_data < 0).any().any():
        raise ValueError("CSV에 음수 값이 있습니다.")

    if (
        numeric_data["collection_duration_seconds"]
        != EXPECTED_DURATION_SECONDS
    ).any():
        raise ValueError(
            "30초가 아닌 수집 구간이 섞여 있습니다. "
            "수집 시간 기준을 먼저 통일하세요."
        )

    for name in COUNT_FEATURES:
        if (numeric_data[name] % 1 != 0).any():
            raise ValueError(
                f"{name}에 정수가 아닌 값이 있습니다."
            )

    features = numeric_data[FEATURE_NAMES].copy()

    # 키보드·마우스·클릭 활동이 모두 없는 구간은
    # 이번 시험 모델의 학습에서 제외
    has_activity = (
        (features["total_keystrokes"] > 0)
        | (features["mouse_move_count"] > 0)
        | (features["click_count"] > 0)
    )

    idle_count = int((~has_activity).sum())

    features = features.loc[
        has_activity
    ].reset_index(drop=True)

    print(f"전체 CSV 행 수: {len(dataframe)}")
    print(f"활동이 없어 제외한 행 수: {idle_count}")
    print(f"사용할 학습 샘플 수: {len(features)}")

    if len(features) < MIN_TRAINING_SAMPLES:
        raise ValueError(
            "시험 학습 데이터가 부족합니다. "
            f"활동이 있는 구간을 {MIN_TRAINING_SAMPLES}개 이상 "
            f"수집하세요. 현재: {len(features)}개"
        )

    constant_columns = [
        name
        for name in FEATURE_NAMES
        if features[name].nunique() <= 1
    ]

    if constant_columns:
        print(
            "주의: 값의 변화가 없는 Feature가 있습니다:",
            constant_columns,
        )

    return features, idle_count


def train_model():
    features, idle_count = load_training_data()

    # Feature별 크기 차이를 표준화
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
    )
    model.fit(scaled_features)

    # 학습 데이터에 대한 판정 분포
    predictions = model.predict(scaled_features)

    normal_count = int((predictions == 1).sum())
    anomaly_count = int((predictions == -1).sum())

    metadata = {
        "feature_names": FEATURE_NAMES,
        "collection_duration_seconds": EXPECTED_DURATION_SECONDS,
        "training_samples": len(features),
        "excluded_idle_samples": idle_count,
        "training_normal_predictions": normal_count,
        "training_anomaly_predictions": anomaly_count,
        "evaluation": "training_data_only",
        "model_parameters": {
            "kernel": "rbf",
            "gamma": "scale",
            "nu": 0.05,
        },
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    with FEATURES_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            FEATURE_NAMES,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with METADATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n키보드 + 마우스 시험 모델 학습 완료")
    print(f"사용 Feature: {FEATURE_NAMES}")
    print(f"학습 데이터 정상 예측 수: {normal_count}")
    print(f"학습 데이터 이상 예측 수: {anomaly_count}")
    print(f"저장 위치: {MODELS_DIR}")
    print("위 판정 개수는 별도 평가 데이터의 정확도가 아닙니다.")


if __name__ == "__main__":
    train_model()