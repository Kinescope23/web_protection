import numpy as np
import joblib
import os
from sklearn.ensemble import IsolationForest, HistGradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

BASE_DIR = "/app/ml_models"
#BASE_DIR = os.path.join(os.path.dirname(__file__), "ml_models")
os.makedirs(BASE_DIR, exist_ok=True)

# Пути к файлам моделей и скейлеров
PATHS = {
    "isolation_forest": {
        "model": os.path.join(BASE_DIR, "isolation_forest.pkl"),
        "scaler": os.path.join(BASE_DIR, "isolation_forest_scaler.pkl"),
    },
    "gradient_boosting": {
        "model": os.path.join(BASE_DIR, "gradient_boosting.pkl"),
        "scaler": os.path.join(BASE_DIR, "gradient_boosting_scaler.pkl"),
    },
}

FEATURE_NAMES = [
    "requests_per_sec", "unique_ips_ratio", "ua_entropy",
    "post_ratio", "error_rate", "avg_inter_arrival_ms"
]

def generate_synthetic_data(n_normal=15000, n_bot=5000):
    np.random.seed(42)

    # Нормальный трафик
    normal = np.column_stack([
        np.random.exponential(2.0, n_normal),
        np.random.normal(0.85, 0.1, n_normal),
        np.random.normal(3.5, 0.3, n_normal),
        np.random.normal(0.2, 0.1, n_normal),
        np.random.normal(0.03, 0.02, n_normal),
        np.random.normal(1500, 500, n_normal)
    ])

    # Бот-трафик
    bot = np.column_stack([
        np.random.exponential(15.0, n_bot),
        np.random.normal(0.3, 0.15, n_bot),
        np.random.normal(1.0, 0.5, n_bot),
        np.random.normal(0.8, 0.1, n_bot),
        np.random.normal(0.15, 0.1, n_bot),
        np.random.normal(100, 50, n_bot)
    ])

    X = np.vstack([normal, bot])
    y = np.array([0] * n_normal + [1] * n_bot) # 0 = человек, 1 = бот

    # Перемешиваем
    indices = np.random.permutation(len(y))
    return X[indices], y[indices]

def train_models():
    print("Генерация данных...")
    X, y = generate_synthetic_data()

    print("\n[1/2] Обучение Isolation Forest...")
    if_scaler = RobustScaler()
    X_scaled_if = if_scaler.fit_transform(X)

    if_model = IsolationForest(
        n_estimators=150,
        contamination=0.15,
        random_state=42,
        n_jobs=-1
    )
    if_model.fit(X_scaled_if)

    joblib.dump(if_model, PATHS["isolation_forest"]["model"])
    joblib.dump(if_scaler, PATHS["isolation_forest"]["scaler"])
    print(f"Isolation Forest сохранен")

    print("\n[2/2] Обучение Gradient Boosting...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    gb_scaler = RobustScaler()
    X_train_sc = gb_scaler.fit_transform(X_train)
    X_test_sc = gb_scaler.transform(X_test)

    gb_model = HistGradientBoostingClassifier(
        max_iter=150,
        max_depth=6,
        learning_rate=0.1,
        random_state=42
    )
    gb_model.fit(X_train_sc, y_train)

    y_prob = gb_model.predict_proba(X_test_sc)[:, 1]
    print(f"Gradient Boosting ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")

    joblib.dump(gb_model, PATHS["gradient_boosting"]["model"])
    joblib.dump(gb_scaler, PATHS["gradient_boosting"]["scaler"])
    print(f"Gradient Boosting сохранен")

    print("\nВсе модели успешно обучены и сохранены!")

if __name__ == "__main__":
    train_models()
