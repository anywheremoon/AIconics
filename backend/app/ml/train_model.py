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

# 학습 Feature로 사용하면 안 되는 식별자·정답 컬럼
EXCLUDED_COLUMNS = {
    "id",
    "user_id",
    "device_id",
    "label",
    "target",
    "class",
    "result",
    "is_anomaly",
}


def load_training_data() -> tuple[pd.DataFrame, list[str]]:
    """CSV를 읽고 학습 가능한 숫자형 Feature를 반환한다."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"데이터셋을 찾을 수 없습니다: {DATASET_PATH}")

    if DATASET_PATH.stat().st_size == 0:
        raise ValueError("merged_dataset.csv가 비어 있습니다.")

    dataframe = pd.read_csv(DATASET_PATH)

    if dataframe.empty:
        raise ValueError("merged_dataset.csv에 학습 데이터가 없습니다.")

    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()

    feature_names = [
        column
        for column in numeric_columns
        if column.lower() not in EXCLUDED_COLUMNS
    ]

    if not feature_names:
        raise ValueError("학습에 사용할 숫자형 Feature 컬럼이 없습니다.")

    features = dataframe[feature_names].copy()

    # 숫자로 변환되지 않는 값은 결측치로 처리
    features = features.apply(pd.to_numeric, errors="coerce")

    # 각 컬럼의 결측치를 해당 컬럼의 중앙값으로 채움
    features = features.fillna(features.median())

    # 전부 결측치였던 컬럼이 남으면 제거
    features = features.dropna(axis=1, how="all")
    feature_names = features.columns.tolist()

    if features.empty:
        raise ValueError("전처리 후 사용할 수 있는 학습 데이터가 없습니다.")

    if len(features) < 10:
        print("경고: 학습 데이터가 10개 미만이라 모델 결과가 불안정할 수 있습니다.")

    return features, feature_names


def train_model() -> None:
    """StandardScaler와 One-Class SVM을 학습하고 파일로 저장한다."""
    features, feature_names = load_training_data()

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
    )
    model.fit(scaled_features)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    with FEATURES_PATH.open("w", encoding="utf-8") as file:
        json.dump(feature_names, file, ensure_ascii=False, indent=2)

    predictions = model.predict(scaled_features)
    normal_count = int((predictions == 1).sum())
    anomaly_count = int((predictions == -1).sum())

    print("모델 학습 완료")
    print(f"학습 데이터 수: {len(features)}")
    print(f"사용 Feature: {feature_names}")
    print(f"정상 예측 수: {normal_count}")
    print(f"이상 예측 수: {anomaly_count}")
    print(f"모델 저장: {MODEL_PATH}")
    print(f"Scaler 저장: {SCALER_PATH}")


if __name__ == "__main__":
    train_model()