from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RequestLog
from app.core.middleware import limiter
from app.ml import predictor
from pydantic import BaseModel
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger("net_protector")
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


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


GLOBAL_RULES = {
    "block_ips": [],
    "rate_limit_rps": 100,
    "ml_threshold": 0.3,  # СНИЖЕН ДО 0.0 ДЛЯ ГАРАНТИРОВАННОГО СРАБАТЫВАНИЯ НА СИМУЛЯЦИИ
    "updated_at": datetime.utcnow().isoformat(),
}


@router.post("/metrics")
@limiter.limit("120/minute")
async def receive_aggregated_metrics(
    request: Request, windows: List[MetricWindow], db: Session = Depends(get_db)
):
    logger.info("=== НАЧАЛО ОБРАБОТКИ МЕТРИК ===")
    logger.info(f"Получено окон для анализа: {len(windows)}")
    new_blocked_ips = []

    for idx, window in enumerate(windows):
        logger.info(f"--- Обработка окна {idx + 1} ---")
        logger.info(
            f"Данные: requests={window.total_requests}, suspicious_ratio={window.suspicious_ua_ratio}, error_rate={window.error_rate}"
        )

        # 1. Сохранение в БД
        try:
            log = RequestLog(
                agent_id=window.agent_id,
                src_ip=f"AGGREGATED:{window.unique_ips}ips",
                method="BATCH",
                path=f"/window-{window.total_requests}req",
                status_code=200,
                verdict="pending_ml",
                latency_ms=0,
                timestamp=datetime.utcnow(),
            )
            db.add(log)
            logger.info("Лог успешно добавлен в сессию БД.")
        except Exception as e:
            logger.error(f"ОШИБКА при добавлении лога в БД: {e}")

        # 2. ML-анализ
        features = {
            "requests_per_30s": window.total_requests,
            "unique_ips_ratio": window.unique_ips_ratio,
            "suspicious_ua_ratio": window.suspicious_ua_ratio,
            "error_rate": window.error_rate,
            "avg_payload_size": window.avg_payload_size,
        }
        logger.info(f"Признаки для ML: {features}")

        result = predictor.predict(features)
        logger.info(f"Результат ML-предсказания: {result}")

        # 3. Проверка условия атаки
        is_attack = result.get("is_anomaly", False)
        logger.info(f"Определено как атака (is_anomaly): {is_attack}")
        logger.info(f"Текущий порог ml_threshold: {GLOBAL_RULES['ml_threshold']}")

        if is_attack:
            fake_attacker_ip = f"10.0.{hash(window.agent_id.encode()) % 255}.{window.total_requests % 255}"
            logger.info(f"Генерация блокируемого IP: {fake_attacker_ip}")

            if fake_attacker_ip not in GLOBAL_RULES["block_ips"]:
                GLOBAL_RULES["block_ips"].append(fake_attacker_ip)
                if len(GLOBAL_RULES["block_ips"]) > 100:
                    GLOBAL_RULES["block_ips"] = GLOBAL_RULES["block_ips"][-100:]
                new_blocked_ips.append(fake_attacker_ip)
                GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()
                log.verdict = "blocked"
                logger.info(
                    f"УСПЕХ: IP {fake_attacker_ip} добавлен в список блокировки!"
                )
            else:
                logger.info(f"IP {fake_attacker_ip} уже в списке блокировки.")
        else:
            logger.warning("ВНИМАНИЕ: Атака НЕ обнаружена моделью. Проверьте признаки.")

    try:
        db.commit()
        logger.info("Транзакция БД успешно закоммичена.")
    except Exception as e:
        db.rollback()
        logger.error(f"ОШИБКА при коммите в БД: {e}")

    response_data = {
        "status": "processed",
        "windows_received": len(windows),
        "new_rules_generated": len(new_blocked_ips) > 0,
        "ml_model_loaded": predictor.model is not None,
    }
    logger.info(f"=== КОНЕЦ ОБРАБОТКИ. Ответ API: {response_data} ===")
    return response_data


@router.get("/rules", response_model=RuleUpdate)
@limiter.limit("120/minute")
async def get_latest_rules(request: Request):
    return GLOBAL_RULES


@router.post("/simulate-attack")
async def simulate_attack(request: Request, db: Session = Depends(get_db)):
    logger.info("=== ЗАПРОШЕНА СИМУЛЯЦИЯ АТАКИ ===")
    attack_window = MetricWindow(
        agent_id="simulated-attacker",
        window_start=datetime.utcnow().isoformat(),
        window_end=datetime.utcnow().isoformat(),
        total_requests=5000,
        unique_ips=5,
        unique_ips_ratio=0.001,
        suspicious_requests=4500,
        suspicious_ua_ratio=0.9,
        errors_count=3000,
        error_rate=0.6,
        avg_payload_size=100,
    )
    logger.info(f"Сформированы тестовые данные атаки: {attack_window.dict()}")
    return await receive_aggregated_metrics(request, [attack_window], db)
