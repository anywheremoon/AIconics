from pathlib import Path
import argparse
import json

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models" / "keyboard_mouse"

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


def evaluate(csv_path):
    csv_path = Path(csv_path)

    model_path = MODEL_DIR / "one_class_svm.pkl"
    scaler_path = MODEL_DIR / "scaler.pkl"
    names_path = MODEL_DIR / "feature_names.json"

    for path in [csv_path, model_path, scaler_path, names_path]:
        if not path.exists():
            raise FileNotFoundError(f"파일이 없습니다: {path}")

    with names_path.open("r", encoding="utf-8") as file:
        saved_names = json.load(file)

    if saved_names != FEATURE_NAMES:
        raise ValueError("모델의 Feature 목록 또는 순서가 다릅니다.")

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    if list(getattr(scaler, "feature_names_in_", [])) != FEATURE_NAMES:
        raise ValueError("Scaler의 Feature 목록이 다릅니다.")

    if getattr(model, "n_features_in_", None) != len(FEATURE_NAMES):
        raise ValueError("모델의 입력 Feature 개수가 다릅니다.")

    dataframe = pd.read_csv(csv_path)

    if dataframe.empty:
        raise ValueError("테스트 CSV에 데이터가 없습니다.")

    required = ["collection_duration_seconds", *FEATURE_NAMES]
    missing = [
        name for name in required
        if name not in dataframe.columns
    ]

    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")

    numeric = dataframe[required].apply(
        pd.to_numeric,
        errors="coerce",
    )

    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("숫자가 아닌 값, 결측치 또는 무한대가 있습니다.")

    if (numeric < 0).any().any():
        raise ValueError("음수 값이 있습니다.")

    if (numeric["collection_duration_seconds"] != 30).any():
        raise ValueError("30초 수집 데이터만 사용할 수 있습니다.")

    for name in COUNT_FEATURES:
        if (numeric[name] % 1 != 0).any():
            raise ValueError(f"{name} 값은 정수여야 합니다.")

    features = numeric[FEATURE_NAMES]

    # 시험 학습 코드와 같은 활동 여부 기준
    has_activity = (
        (features["total_keystrokes"] > 0)
        | (features["mouse_move_count"] > 0)
        | (features["click_count"] > 0)
    )

    result = dataframe.copy()
    result["ml_status"] = "SKIPPED_NO_ACTIVITY"
    result["prediction"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="Int64",
    )
    result["decision_score"] = np.nan

    if has_activity.any():
        scaled = scaler.transform(
            features.loc[has_activity]
        )

        predictions = model.predict(scaled)
        scores = model.decision_function(scaled)

        result.loc[has_activity, "ml_status"] = [
            "NORMAL" if value == 1 else "ANOMALY"
            for value in predictions
        ]
        result.loc[has_activity, "prediction"] = predictions
        result.loc[has_activity, "decision_score"] = scores

    output_path = csv_path.with_name(
        f"{csv_path.stem}_predictions.csv"
    )
    result.to_csv(output_path, index=False)

    print("키보드 + 마우스 시험 예측 완료")
    print(result["ml_status"].value_counts().to_string())
    print(f"\n결과 저장: {output_path}")
    print("decision_score는 확률이 아닙니다.")
    print("정답 라벨이 없으므로 정확도는 계산하지 않습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csv_path",
        help="시험 예측에 사용할 CSV 경로",
    )
    args = parser.parse_args()

    evaluate(args.csv_path)