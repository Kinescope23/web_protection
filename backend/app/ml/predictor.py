"""
Сервис предсказания аномалий с использованием обученной модели.
"""
import joblib
import numpy as np
import os
from typing import List, Dict

MODEL_PATH = "/app/ml_models/isolation_forest.pkl"
NORM_PATH = "/app/ml_models/isolation_forest_norm.pkl"


class MLPredictor:
    def __init__(self):
        self.model = None
        self.norm_params = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            self.norm_params = joblib.load(NORM_PATH)
            print(f"✅ ML-модель загружена: {MODEL_PATH}")
        else:
            print("⚠️ ML-модель не найдена. Запустите: python -m app.ml.train")

    def predict(self, features: Dict) -> Dict:
        """
        Предсказывает аномальность окна метрик.

        Args:
            features: словарь с признаками:
                - requests_per_30s: int
                - unique_ips_ratio: float (0-1)
                - suspicious_ua_ratio: float (0-1)
                - error_rate: float (0-1)
                - avg_payload_size: int

        Returns:
            dict с полями:
                - is_anomaly: bool
                - anomaly_score: float (-1 до 0, меньше = аномальнее)
        """
        if not self.model:
            return {"is_anomaly": False, "anomaly_score": 0.0, "error": "model_not_loaded"}

        # Формируем вектор признаков в правильном порядке
        feature_vector = np.array([[
            features.get("requests_per_30s", 0),
            features.get("unique_ips_ratio", 0.5),
            features.get("suspicious_ua_ratio", 0.05),
            features.get("error_rate", 0.02),
            features.get("avg_payload_size", 500),
        ]])

        # Нормализация
        feature_norm = (feature_vector - self.norm_params["min"]) / (
                np.array(self.norm_params["max"]) - np.array(self.norm_params["min"]) + 1e-8
        )

        # Предсказание: 1 = нормальный, -1 = аномалия
        prediction = self.model.predict(feature_norm)[0]
        score = self.model.decision_function(feature_norm)[0]

        return {
            "is_anomaly": prediction == -1,
            "anomaly_score": float(score),
            "prediction": int(prediction)
        }


# Глобальный экземпляр
predictor = MLPredictor()