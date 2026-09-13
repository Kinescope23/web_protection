
import os
import joblib
import numpy as np
from typing import Dict, Literal

BASE_DIR = "/app/ml_models"

ModelType = Literal["isolation_forest", "gradient_boosting"]

class BotTrafficPredictor:
    AVAILABLE_MODELS: tuple[ModelType, ...] = ("isolation_forest", "gradient_boosting")

    def __init__(self):
        self.feature_names = [
            "requests_per_sec", "unique_ips_ratio", "ua_entropy",
            "post_ratio", "error_rate", "avg_inter_arrival_ms"
        ]
        self.models: Dict[str, object] = {}
        self.scalers: Dict[str, object] = {}
        self._load_all()

    def _load_all(self):
        for model_name in self.AVAILABLE_MODELS:
            model_path = os.path.join(BASE_DIR, f"{model_name}.pkl")
            scaler_path = os.path.join(BASE_DIR, f"{model_name}_scaler.pkl")

            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.models[model_name] = joblib.load(model_path)
                self.scalers[model_name] = joblib.load(scaler_path)
                print(f"{model_name} loaded")
            else:
                print(f"{model_name} not loaded")

    def _prepare_vector(self, features: Dict) -> np.ndarray:
        defaults = {
            "requests_per_sec": 1.0,
            "unique_ips_ratio": 0.8,
            "ua_entropy": 3.5,
            "post_ratio": 0.2,
            "error_rate": 0.03,
            "avg_inter_arrival_ms": 1000.0
        }
        vec = [features.get(f, defaults[f]) for f in self.feature_names]
        return np.array([vec])

    def predict(self, features: Dict, model_name: str = "isolation_forest") -> Dict:

        if model_name not in self.AVAILABLE_MODELS:
            return {"error": f"Unknown model. Available: {self.AVAILABLE_MODELS}"}

        if model_name not in self.models:
            return {"error": f"Model '{model_name}' is not loaded on server."}

        vector = self._prepare_vector(features)
        scaled_vector = self.scalers[model_name].transform(vector)

        if model_name == "isolation_forest":
            return self._process_isolation_forest(scaled_vector)
        elif model_name == "gradient_boosting":
            return self._process_gradient_boosting(scaled_vector)

    def _process_isolation_forest(self, X_scaled: np.ndarray) -> Dict:
        """Обрабатывает результат IF (score -> probability)."""
        model = self.models["isolation_forest"]
        score = model.decision_function(X_scaled)[0]

        prob = 1.0 / (1.0 + np.exp(score * 8))

        return self._format_result(probability=prob, model_used="isolation_forest", raw_score=score)

    def _process_gradient_boosting(self, X_scaled: np.ndarray) -> Dict:
        model = self.models["gradient_boosting"]
        prob = float(model.predict_proba(X_scaled)[0][1])
        return self._format_result(probability=prob, model_used="gradient_boosting", raw_score=prob)

    def _format_result(self, probability: float, model_used: str, raw_score: float) -> Dict:
        is_bot = probability > 0.65

        if probability < 0.4:
            risk = "low"
        elif probability < 0.75:
            risk = "medium"
        else:
            risk = "high"

        return {
            "is_bot": bool(is_bot),
            "bot_probability": round(float(probability), 4),
            "risk_level": risk,
            "raw_score": round(float(raw_score), 4),
            "model_used": model_used
        }

predictor = BotTrafficPredictor()
