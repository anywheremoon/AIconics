from pathlib import Path
import joblib
import numpy as np
import pandas as pd


# 현재 파일:
# backend/app/ml/services/anomaly_detector.py
#
# 모델 폴더:
# backend/app/ml/models/
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

MODEL_PATH = MODEL_DIR / "one_class_svm.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"


class AnomalyDetector:
    """
    저장된 Scaler와 One-Class SVM 모델을 이용하여
    사용자 행동 데이터의 이상 여부를 판단한다.
    """

    def __init__(self):
        self.model = None
        self.scaler = None

        self.load_models()

    def load_models(self):
        """
        B가 생성한 모델과 Scaler를 불러온다.
        """

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"One-Class SVM 모델 파일이 없습니다: {MODEL_PATH}"
            )

        if not SCALER_PATH.exists():
            raise FileNotFoundError(
                f"Scaler 파일이 없습니다: {SCALER_PATH}"
            )

        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)

        print("One-Class SVM 모델 로드 완료")
        print("Scaler 로드 완료")

    def predict(self, features: list[float]) -> dict:
        """
        Feature 목록을 받아 이상 여부와 이상 점수를 반환한다.

        One-Class SVM 결과
        1  : 정상
        -1 : 이상
        """

        if not features:
            raise ValueError("입력된 Feature가 없습니다.")

        # 모델은 2차원 형태를 요구함
        feature_names = list(getattr(self.scaler, "feature_names_in_", []))
        if feature_names and len(features) != len(feature_names):
            raise ValueError(
                f"Expected {len(feature_names)} ML features, received {len(features)}."
            )

        feature_array = np.asarray(
            features,
            dtype=float
        ).reshape(1, -1)
        model_input = (
            pd.DataFrame(feature_array, columns=feature_names)
            if feature_names
            else feature_array
        )

        # 학습할 때 사용한 Scaler 적용
        scaled_features = self.scaler.transform(model_input)

        # 정상 1, 이상 -1
        prediction = int(
            self.model.predict(scaled_features)[0]
        )

        # decision_function 값이 작을수록 이상 가능성이 큼
        decision_score = float(
            self.model.decision_function(scaled_features)[0]
        )

        return {
            "prediction": prediction,
            "is_anomaly": prediction == -1,
            "decision_score": decision_score
        }


# API 요청마다 모델을 다시 불러오지 않도록 한 번만 생성
anomaly_detector = AnomalyDetector()
