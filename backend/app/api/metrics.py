from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RequestLog, User
from app.core.middleware import limiter
from app.ml import predictor
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/v1/sentinel", tags=["sentinel"])


class MetricWindow(BaseModel):
    agent_id: str
    window_start: str
    window_end: str
    total_requests: int
    unique_ips: int
    unique_ips_ratio: float
    suspicious_requests: int
    suspicious_ua_ratio: float
    errors_count: int
    error_rate: float
    avg_payload_size: int


class RuleUpdate(BaseModel):
    block_ips: List[str]
    rate_limit_rps: int
    ml_threshold: float
    updated_at: str


# Глобальное хранилище правил
GLOBAL_RULES = {
    "block_ips": [],
    "rate_limit_rps": 100,
    "ml_threshold": 0.3,
    "updated_at": datetime.utcnow().isoformat()
}


@router.post("/metrics")
@limiter.limit("120/minute")
async def receive_aggregated_metrics(
        request: Request,
        windows: List[MetricWindow],
        db: Session = Depends(get_db)
):
    """
    Принимает агрегированные метрики от агента (окно 30 сек).
    Применяет ML-модель Isolation Forest для детектирования аномалий.
    """
    new_blocked_ips = []

    for window in windows:
        # 1. Сохраняем агрегированные метрики в БД
        log = RequestLog(
            agent_id=window.agent_id,
            src_ip=f"AGGREGATED:{window.unique_ips}ips",
            method="BATCH",
            path=f"/window-{window.total_requests}req",
            status_code=200,
            verdict="allowed",
            latency_ms=0,
            timestamp=datetime.utcnow()
        )
        db.add(log)

        # 2. ML-анализ через Isolation Forest
        features = {
            "requests_per_30s": window.total_requests,
            "unique_ips_ratio": window.unique_ips_ratio,
            "suspicious_ua_ratio": window.suspicious_ua_ratio,
            "error_rate": window.error_rate,
            "avg_payload_size": window.avg_payload_size,
        }

        result = predictor.predict(features)

        # 3. Применяем порог чувствительности из настроек админа
        is_attack = (
                result.get("is_anomaly", False) and
                abs(result.get("anomaly_score", 0)) > GLOBAL_RULES["ml_threshold"]
        )

        if is_attack:
            # Блокируем "самый частый IP" из этого окна (демо-логика)
            # В реальности агент должен присылать список подозрительных IP
            fake_attacker_ip = f"10.0.{hash(window.agent_id) % 255}.{window.total_requests % 255}"
            if fake_attacker_ip not in GLOBAL_RULES["block_ips"]:
                GLOBAL_RULES["block_ips"].append(fake_attacker_ip)
                # Ограничиваем список до 100 IP
                if len(GLOBAL_RULES["block_ips"]) > 100:
                    GLOBAL_RULES["block_ips"] = GLOBAL_RULES["block_ips"][-100:]
                new_blocked_ips.append(fake_attacker_ip)
                GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

                # Обновляем вердикт в БД
                log.verdict = "blocked"

        print(f"🤖 ML-анализ: agent={window.agent_id}, "
              f"requests={window.total_requests}, "
              f"score={result.get('anomaly_score', 0):.3f}, "
              f"is_attack={is_attack}")

    db.commit()

    return {
        "status": "processed",
        "windows_received": len(windows),
        "new_rules_generated": len(new_blocked_ips) > 0,
        "ml_model_loaded": predictor.model is not None
    }


@router.get("/rules", response_model=RuleUpdate)
@limiter.limit("120/minute")
async def get_latest_rules(request: Request):
    """
    Эндпоинт для опроса агентами каждую 1 секунду.
    """
    return GLOBAL_RULES


@router.post("/simulate-attack")
async def simulate_attack(request: Request, db: Session = Depends(get_db)):
    """
    Тестовый эндпоинт для имитации атаки (для демонстрации ML).
    """
    attack_window = MetricWindow(
        agent_id="simulated-attacker",
        window_start=datetime.utcnow().isoformat(),
        window_end=datetime.utcnow().isoformat(),
        total_requests=5000,  # Много запросов
        unique_ips=5,  # Мало уникальных IP (ботнет)
        unique_ips_ratio=0.001,
        suspicious_requests=4500,
        suspicious_ua_ratio=0.9,
        errors_count=3000,
        error_rate=0.6,
        avg_payload_size=100
    )
    return await receive_aggregated_metrics(request, [attack_window], db)


@router.get("/health")
def sentinel_health():
    return {
        "status": "ok",
        "ml_model_loaded": predictor.model is not None,
        "active_blocked_ips": len(GLOBAL_RULES["block_ips"]),
        "ml_threshold": GLOBAL_RULES["ml_threshold"]
    }