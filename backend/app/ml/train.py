"""
Скрипт обучения улучшенной модели обнаружения ботов.
Используем HistGradientBoostingClassifier для высокой точности и RobustScaler для устойчивости к выбросам.
"""
import numpy as np
import joblib
import os
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

MODEL_PATH = "/app/ml_models/bot_detector.pkl"
SCALER_PATH = "/app/ml_models/bot_detector_scaler.pkl"

os.makedirs("/app/ml_models", exist_ok=True)

def generate_realistic_synthetic_data(n_normal=15000, n_bot=5000):
    """
    Генерирует синтетические данные с перекрытием распределений,
    имитируя реальный мир, где поведение иногда пересекается.
    """
    np.random.seed(42)

    # Нормальный трафик (люди)
    normal = np.column_stack([
        np.random.exponential(scale=2.0, size=n_normal),          # requests_per_sec (низкая)
        np.random.normal(0.85, 0.1, n_normal),                    # unique_ips_ratio (высокая)
        np.random.normal(3.5, 0.3, n_normal),                     # ua_entropy (высокая, разные браузеры)
        np.random.normal(0.2, 0.1, n_normal),                     # post_ratio
        np.random.normal(0.03, 0.02, n_normal),                   # error_rate
        np.random.normal(1500, 500, n_normal)                     # avg_inter_arrival_ms (медленно)
    ])

    # Бот-трафик (скрипты, DDoS, скраперы)
    bot = np.column_stack([
        np.random.exponential(scale=15.0, size=n_bot),            # requests_per_sec (высокая)
        np.random.normal(0.3, 0.15, n_bot),                       # unique_ips_ratio (низкая)
        np.random.normal(1.0, 0.5, n_bot),                        # ua_entropy (низкая, одинаковый UA)
        np.random.normal(0.8, 0.1, n_bot),                        # post_ratio (атаки на формы)
        np.random.normal(0.15, 0.1, n_bot),                       # error_rate (выше из-за блокировок)
        np.random.normal(100, 50, n_bot)                          # avg_inter_arrival_ms (очень быстро)
    ])

    X = np.vstack([normal, bot])
    y = np.array([0] * n_normal + [1] * n_bot) # 0 = человек, 1 = бот

    # Перемешиваем данные
    indices = np.random.permutation(len(y))
    return X[indices], y[indices]

def train_model():
    print("🤖 Генерация данных и обучение модели...")
    X, y = generate_realistic_synthetic_data()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # RobustScaler использует медиану и интерквартильный размах, игнорируя экстремальные выбросы
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.1,
        max_depth=6,
        random_state=42
    )

    model.fit(X_train_scaled, y_train)

    # Оценка качества
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    print("\n📊 Отчет о классификации:")
    print(classification_report(y_test, y_pred, target_names=["Human", "Bot"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

    # Сохранение артефактов
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"✅ Модель сохранена: {MODEL_PATH}")
    print(f"✅ Скейлер сохранен: {SCALER_PATH}")

if __name__ == "__main__":
    train_model()
