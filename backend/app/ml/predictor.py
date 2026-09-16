import os
import joblib
import numpy as np
from typing import Dict, List

BASE_DIR = "/app/ml_models"


class BotTrafficPredictor:
    # Классовая константа — список ВСЕХ ВОЗМОЖНЫХ моделей
    AVAILABLE_MODELS = ("isolation_forest", "gradient_boosting")

    def __init__(self):
        self.feature_names = [
            "requests_per_sec", "unique_ips_ratio", "ua_entropy",
            "post_ratio", "error_rate", "avg_inter_arrival_ms"
        ]
        self.models: Dict[str, object] = {}
        self.scalers: Dict[str, object] = {}
        self._load_all()

    def _load_all(self):
        self.models.clear()
        self.scalers.clear()
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR, exist_ok=True)
            return

        for filename in os.listdir(BASE_DIR):
            if filename.endswith(".pkl") and not filename.endswith("_scaler.pkl"):
                model_name = filename[:-4]
                model_path = os.path.join(BASE_DIR, filename)
                scaler_path = os.path.join(BASE_DIR, f"{model_name}_scaler.pkl")

                if os.path.exists(scaler_path):
                    try:
                        self.models[model_name] = joblib.load(model_path)
                        self.scalers[model_name] = joblib.load(scaler_path)
                        print(f"[ML] {model_name} loaded successfully")
                    except Exception as e:
                        print(f"[ML] Failed to load {model_name}: {e}")
                else:
                    print(f"[ML] {model_name} skipped (scaler not found)")

    # Property — список ЗАГРУЖЕННЫХ моделей (для UI)
    @property
    def available_models(self) -> List[str]:
        return list(self.models.keys())

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

    def predict(self, features: Dict, model_name: str) -> Dict:
        if model_name not in self.AVAILABLE_MODELS:
            return {"error": f"Model '{model_name}' not in AVAILABLE_MODELS. Available: {self.AVAILABLE_MODELS}"}
        if model_name not in self.models:
            return {"error": f"Model '{model_name}' is not loaded on server."}

        vector = self._prepare_vector(features)
        scaled_vector = self.scalers[model_name].transform(vector)

        if model_name == "isolation_forest":
            return self._process_isolation_forest(scaled_vector)
        else:
            return self._process_gradient_boosting(scaled_vector, model_name)

    def _process_isolation_forest(self, X_scaled: np.ndarray) -> Dict:
        model = self.models["isolation_forest"]
        score = model.decision_function(X_scaled)[0]
        prob = 1.0 / (1.0 + np.exp(score * 8))
        return self._format_result(probability=prob, model_used="isolation_forest", raw_score=score)

    def _process_gradient_boosting(self, X_scaled: np.ndarray, model_name: str) -> Dict:
        model = self.models[model_name]
        prob = float(model.predict_proba(X_scaled)[0][1])
        return self._format_result(probability=prob, model_used=model_name, raw_score=prob)

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