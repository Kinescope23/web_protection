from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.models import RequestLog, Agent, UserMLSettings, User
from app.core.middleware import limiter
from app.ml import predictor
from pydantic import BaseModel

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
    requests_per_sec: float = 1.0
    ua_entropy: float = 3.5
    post_ratio: float = 0.2
    avg_inter_arrival_ms: float = 1000.0


class RuleUpdate(BaseModel):
    block_ips: List[str]
    rate_limit_rps: int
    ml_threshold: float
    updated_at: str


# Глобальное хранилище правил
GLOBAL_RULES = {
    "block_ips": [],
    "rate_limit_rps": 100,
    "updated_at": datetime.utcnow().isoformat()
}


def get_user_ml_settings(db: Session, user_id: int) -> dict:
    settings = db.query(UserMLSettings).filter(UserMLSettings.user_id == user_id).first()
    if not settings:
        settings = UserMLSettings(user_id=user_id, ml_model="isolation_forest", ml_threshold=0.65)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return {"ml_model": settings.ml_model, "ml_threshold": settings.ml_threshold}


@router.post("/metrics")
@limiter.limit("120/minute")
async def receive_aggregated_metrics(
    request: Request,
    windows: List[MetricWindow],
    db: Session = Depends(get_db)
):
    new_blocked_ips = []

    for window in windows:
        # Находим агента и его владельца
        agent = db.query(Agent).filter(Agent.agent_id == window.agent_id).first()

        # Если агент не зарегистрирован админом — пропускаем метрики
        if not agent:
            print(f"[Agent] Агент '{window.agent_id}' не зарегистрирован. "
                  f"Попросите администратора создать его в панели управления.")
            continue

        # Обновляем last_seen
        agent.last_seen = datetime.utcnow()

        # Получаем per-user настройки ML
        user_settings = get_user_ml_settings(db, agent.user_id)
        active_model = user_settings["ml_model"]
        threshold = user_settings["ml_threshold"]

        features = {
            "requests_per_sec": window.requests_per_sec,
            "unique_ips_ratio": window.unique_ips_ratio,
            "ua_entropy": window.ua_entropy,
            "post_ratio": window.post_ratio,
            "error_rate": window.error_rate,
            "avg_inter_arrival_ms": window.avg_inter_arrival_ms,
        }

        result = predictor.predict(features, model_name=active_model)
        bot_probability = result.get("bot_probability", 0.0)
        risk_level = result.get("risk_level", "low")
        is_bot = result.get("is_bot", False)
        is_attack = bot_probability > threshold

        verdict = "blocked" if is_attack else "allowed"
        log = RequestLog(
            agent_id=window.agent_id,
            src_ip=f"AGGREGATED:{window.unique_ips}ips",
            method="BATCH",
            path=f"/window-{window.total_requests}req",
            status_code=200,
            verdict=verdict,
            latency_ms=0,
            bot_probability=bot_probability,
            risk_level=risk_level,
            ml_model_used=active_model,
            is_bot=is_bot,
            timestamp=datetime.utcnow()
        )
        db.add(log)

        if is_attack:
            fake_ip = f"10.0.{hash(window.agent_id) % 255}.{window.total_requests % 255}"
            if fake_ip not in GLOBAL_RULES["block_ips"]:
                GLOBAL_RULES["block_ips"].append(fake_ip)
                if len(GLOBAL_RULES["block_ips"]) > 100:
                    GLOBAL_RULES["block_ips"] = GLOBAL_RULES["block_ips"][-100:]
                new_blocked_ips.append(fake_ip)
                GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

        print(f"[ML] agent={window.agent_id}, user={agent.user_id}, "
              f"model={active_model}, threshold={threshold}, "
              f"bot_prob={bot_probability:.3f}, risk={risk_level}")

        # Получаем per-user настройки ML
        user_settings = get_user_ml_settings(db, agent.user_id)
        active_model = user_settings["ml_model"]
        threshold = user_settings["ml_threshold"]

        features = {
            "requests_per_sec": window.requests_per_sec,
            "unique_ips_ratio": window.unique_ips_ratio,
            "ua_entropy": window.ua_entropy,
            "post_ratio": window.post_ratio,
            "error_rate": window.error_rate,
            "avg_inter_arrival_ms": window.avg_inter_arrival_ms,
        }

        result = predictor.predict(features, model_name=active_model)
        bot_probability = result.get("bot_probability", 0.0)
        risk_level = result.get("risk_level", "low")
        is_bot = result.get("is_bot", False)
        is_attack = bot_probability > threshold

        verdict = "blocked" if is_attack else "allowed"
        log = RequestLog(
            agent_id=window.agent_id,
            src_ip=f"AGGREGATED:{window.unique_ips}ips",
            method="BATCH",
            path=f"/window-{window.total_requests}req",
            status_code=200,
            verdict=verdict,
            latency_ms=0,
            bot_probability=bot_probability,
            risk_level=risk_level,
            ml_model_used=active_model,
            is_bot=is_bot,
            timestamp=datetime.utcnow()
        )
        db.add(log)

        if is_attack:
            fake_ip = f"10.0.{hash(window.agent_id) % 255}.{window.total_requests % 255}"
            if fake_ip not in GLOBAL_RULES["block_ips"]:
                GLOBAL_RULES["block_ips"].append(fake_ip)
                if len(GLOBAL_RULES["block_ips"]) > 100:
                    GLOBAL_RULES["block_ips"] = GLOBAL_RULES["block_ips"][-100:]
                new_blocked_ips.append(fake_ip)
                GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

        print(f"[ML] agent={window.agent_id}, user={agent.user_id}, "
              f"model={active_model}, threshold={threshold}, "
              f"bot_prob={bot_probability:.3f}, risk={risk_level}")

    db.commit()

    return {
        "status": "processed",
        "windows_received": len(windows),
        "new_rules_generated": len(new_blocked_ips) > 0
    }


@router.get("/rules", response_model=RuleUpdate)
@limiter.limit("120/minute")
async def get_latest_rules(request: Request):
    return {
        "block_ips": GLOBAL_RULES["block_ips"],
        "rate_limit_rps": GLOBAL_RULES["rate_limit_rps"],
        "ml_threshold": 0.65,
        "updated_at": GLOBAL_RULES["updated_at"]
    }


@router.post("/simulate-attack")
async def simulate_attack(request: Request, db: Session = Depends(get_db)):
    attack_window = MetricWindow(
        agent_id="agent-001",
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
        requests_per_sec=150.0,
        ua_entropy=1.0,
        post_ratio=0.8,
        avg_inter_arrival_ms=50.0
    )
    return await receive_aggregated_metrics(request, [attack_window], db)


@router.get("/health")
def agent_health():
    return {
        "status": "ok",
        "models_loaded": list(predictor.models.keys()),
        "active_blocked_ips": len(GLOBAL_RULES["block_ips"])
    }