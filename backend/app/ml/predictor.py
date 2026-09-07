"""
Сервис предсказания бот-трафика с использованием улучшенной модели.
"""
import joblib
import numpy as np
import os
from typing import Dict

MODEL_PATH = "/app/ml_models/bot_detector.pkl"
SCALER_PATH = "/app/ml_models/bot_detector_scaler.pkl"

class BotPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            "requests_per_sec", "unique_ips_ratio", "ua_entropy",
            "post_ratio", "error_rate", "avg_inter_arrival_ms"
        ]
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            print(f"✅ ML-модель и скейлер успешно загружены")
        else:
            print("⚠️ ML-модель не найдена. Запустите: python -m app.ml.train")

    def predict(self, features: Dict) -> Dict:
        """
        Предсказывает вероятность того, что трафик является ботом.
        """
        if not self.model or not self.scaler:
            return {"is_bot": False, "bot_probability": 0.0, "error": "model_not_loaded"}

        # Извлекаем признаки в строгом порядке. Дефолтные значения настроены на "безопасного" пользователя.
        feature_vector = np.array([[
            features.get("requests_per_sec", 1.0),
            features.get("unique_ips_ratio", 0.8),
            features.get("ua_entropy", 3.5),
            features.get("post_ratio", 0.2),
            features.get("error_rate", 0.03),
            features.get("avg_inter_arrival_ms", 1000.0)
        ]])

        # Нормализация
        feature_scaled = self.scaler.transform(feature_vector)

        # Получаем вероятность класса 1 (бот)
        bot_probability = float(self.model.predict_proba(feature_scaled)[0][1])

        # Порог можно вынести в конфигурацию
        is_bot = bot_probability > 0.65

        # Оценка уровня риска для гибкой реакции бэкенда
        if bot_probability < 0.4:
            risk_level = "low"
        elif bot_probability < 0.75:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "is_bot": bool(is_bot),
            "bot_probability": round(bot_probability, 4),
            "risk_level": risk_level
        }

# Глобальный экземпляр для импорта
predictor = BotPredictor()
