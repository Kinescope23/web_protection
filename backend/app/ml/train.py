"""
Скрипт обучения модели Isolation Forest.
Обучается на синтетических данных (нормальный трафик + аномалии).
"""
import numpy as np
import joblib
import os
from sklearn.ensemble import IsolationForest

MODEL_PATH = "/app/ml_models/isolation_forest.pkl"
os.makedirs("/app/ml_models", exist_ok=True)


def generate_synthetic_data(n_normal=10000, n_anomaly=500):
    """
    Генерирует синтетические данные для обучения.
    Признаки (features):
    - requests_per_30s: количество запросов за 30 секунд
    - unique_ips_ratio: доля уникальных IP
    - suspicious_ua_ratio: доля подозрительных User-Agent
    - error_rate: доля 4xx/5xx ответов
    - avg_payload_size: средний размер запроса (байты)
    """
    np.random.seed(42)

    # Нормальный трафик (низкие значения)
    normal = np.column_stack([
        np.random.normal(50, 20, n_normal),  # requests_per_30s
        np.random.normal(0.7, 0.1, n_normal),  # unique_ips_ratio
        np.random.normal(0.05, 0.02, n_normal),  # suspicious_ua_ratio
        np.random.normal(0.02, 0.01, n_normal),  # error_rate
        np.random.normal(500, 200, n_normal),  # avg_payload_size
    ])

    # Аномальный трафик (высокие значения - атака)
    anomaly = np.column_stack([
        np.random.normal(5000, 1000, n_anomaly),  # Много запросов (флуд)
        np.random.normal(0.1, 0.05, n_anomaly),  # Мало уникальных IP (ботнет)
        np.random.normal(0.8, 0.1, n_anomaly),  # Много подозрительных UA
        np.random.normal(0.6, 0.1, n_anomaly),  # Много ошибок
        np.random.normal(100, 50, n_anomaly),  # Маленькие запросы (флуд)
    ])

    # Объединяем и нормализуем
    data = np.vstack([normal, anomaly])
    # Нормализация min-max для каждого признака
    data_min = data.min(axis=0)
    data_max = data.max(axis=0)
    data_norm = (data - data_min) / (data_max - data_min + 1e-8)

    return data_norm


def train_model():
    print("🤖 Обучение модели Isolation Forest...")

    X = generate_synthetic_data()

    # contamination - ожидаемая доля аномалий в данных
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,  # 5% аномалий
        max_samples='auto',
        random_state=42,
        n_jobs=-1
    )

    model.fit(X)
    joblib.dump(model, MODEL_PATH)

    # Сохраняем параметры нормализации для продакшена
    normalization_params = {
        "min": X.min(axis=0).tolist(),
        "max": X.max(axis=0).tolist()
    }
    joblib.dump(normalization_params, MODEL_PATH.replace(".pkl", "_norm.pkl"))

    print(f"✅ Модель сохранена: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_model()