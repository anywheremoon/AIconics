from pathlib import Path
import argparse
import json

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = BASE_DIR / "datasets" / "merged_dataset.csv"

MODEL_PATH = BASE_DIR / "models" / "one_class_svm.pkl"
SCALER_PATH = BASE_DIR / "models" / "scaler.pkl"
FEATURES_PATH = BASE_DIR / "models" / "feature_names.json"


def load_saved_files():
    """학습된 모델, Scaler, Feature 목록을 불러온다."""
    required_files = [MODEL_PATH, SCALER_PATH, FEATURES_PATH]

    for path in required_files:
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(
                f"필요한 파일이 없거나 비어 있습니다: {path}\n"
                "먼저 train_model.py를 실행하세요."
            )

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    with FEATURES_PATH.open("r", encoding="utf-8") as file:
        feature_names = json.load(file)

    return model, scaler, feature_names


def test_model(csv_path: Path) -> None:
    """CSV 데이터를 입력받아 정상 또는 이상 여부를 예측한다."""
    if not csv_path.exists():
        raise FileNotFoundError(f"테스트 CSV를 찾을 수 없습니다: {csv_path}")

    if csv_path.stat().st_size == 0:
        raise ValueError("테스트 CSV가 비어 있습니다.")

    model, scaler, feature_names = load_saved_files()
    dataframe = pd.read_csv(csv_path)

    missing_columns = [
        column for column in feature_names if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"테스트 CSV에 필요한 컬럼이 없습니다: {missing_columns}"
        )

    features = dataframe[feature_names].copy()
    features = features.apply(pd.to_numeric, errors="coerce")
    features = features.fillna(features.median()).fillna(0)

    scaled_features = scaler.transform(features)
    predictions = model.predict(scaled_features)
    anomaly_scores = model.decision_function(scaled_features)

    results = dataframe.copy()
    results["prediction"] = predictions
    results["status"] = [
        "정상" if prediction == 1 else "이상"
        for prediction in predictions
    ]
    results["anomaly_score"] = anomaly_scores

    print(results[feature_names + ["prediction", "status", "anomaly_score"]])
    print()
    print(f"정상 데이터: {(predictions == 1).sum()}개")
    print(f"이상 데이터: {(predictions == -1).sum()}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="저장된 One-Class SVM 모델 테스트"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="테스트할 CSV 파일 경로",
    )
    arguments = parser.parse_args()

    test_model(arguments.csv)