from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.models import User, RequestLog, InvitationKey
from app.api.deps import get_current_user
from app.api.metrics import GLOBAL_RULES
from app.core.middleware import limiter
from app.ml import predictor

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
@limiter.limit("60/minute")
def get_dashboard_stats(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Общая статистика для дашборда.
    Админ видит все данные, обычный пользователь — только свои.
    """
    now = datetime.utcnow()
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)

    # Базовые запросы
    logs_query = db.query(RequestLog)
    if user.role != "admin":
        # Обычный пользователь видит только свои данные (пока — все, т.к. агенты общие)
        pass

    # Статистика за последний час
    last_hour_stats = logs_query.filter(RequestLog.timestamp >= last_hour).all()
    total_requests_1h = len(last_hour_stats)
    blocked_1h = sum(1 for l in last_hour_stats if l.verdict == "blocked")
    bot_detected_1h = sum(1 for l in last_hour_stats if l.is_bot)

    # Статистика за последние 24 часа
    last_24h_stats = logs_query.filter(RequestLog.timestamp >= last_24h).all()
    total_requests_24h = len(last_24h_stats)
    blocked_24h = sum(1 for l in last_24h_stats if l.verdict == "blocked")
    bot_detected_24h = sum(1 for l in last_24h_stats if l.is_bot)

    # Распределение по уровню риска
    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    for log in last_hour_stats:
        if log.risk_level in risk_distribution:
            risk_distribution[log.risk_level] += 1

    # Средняя вероятность бота
    avg_bot_prob = 0.0
    if last_hour_stats:
        probs = [l.bot_probability for l in last_hour_stats if l.bot_probability is not None]
        if probs:
            avg_bot_prob = sum(probs) / len(probs)

    return {
        "last_hour": {
            "total_requests": total_requests_1h,
            "blocked": blocked_1h,
            "bot_detected": bot_detected_1h,
            "avg_bot_probability": round(avg_bot_prob, 4),
        },
        "last_24h": {
            "total_requests": total_requests_24h,
            "blocked": blocked_24h,
            "bot_detected": bot_detected_24h,
        },
        "risk_distribution": risk_distribution,
        "active_blocked_ips": len(GLOBAL_RULES["block_ips"]),
        "ml_model": GLOBAL_RULES["ml_model"],
        "ml_threshold": GLOBAL_RULES["ml_threshold"],
        "models_loaded": list(predictor.models.keys()),
    }


@router.get("/recent-logs")
@limiter.limit("60/minute")
def get_recent_logs(
    request: Request,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Последние логи запросов с ML-анализом"""
    if limit > 100:
        limit = 100

    logs = db.query(RequestLog).order_by(desc(RequestLog.timestamp)).limit(limit).all()

    return [
        {
            "id": log.id,
            "agent_id": log.agent_id,
            "src_ip": log.src_ip,
            "method": log.method,
            "path": log.path,
            "verdict": log.verdict,
            "bot_probability": log.bot_probability,
            "risk_level": log.risk_level,
            "is_bot": log.is_bot,
            "ml_model_used": log.ml_model_used,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]


@router.get("/threats")
@limiter.limit("60/minute")
def get_active_threats(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Список активных угроз (заблокированные IP + последние обнаруженные боты)"""
    now = datetime.utcnow()
    last_hour = now - timedelta(hours=1)

    # 1. Активно заблокированные IP из GLOBAL_RULES
    blocked_ips = [
        {
            "type": "blocked_ip",
            "value": ip,
            "severity": "high",
            "source": "global_rules",
            "detected_at": GLOBAL_RULES["updated_at"],
        }
        for ip in GLOBAL_RULES["block_ips"]
    ]

    # 2. Последние обнаруженные боты из БД
    recent_bots = db.query(RequestLog).filter(
        RequestLog.is_bot == True,
        RequestLog.timestamp >= last_hour
    ).order_by(desc(RequestLog.timestamp)).limit(10).all()

    bot_threats = [
        {
            "type": "bot_detected",
            "value": log.src_ip,
            "severity": log.risk_level or "medium",
            "source": log.ml_model_used or "unknown",
            "detected_at": log.timestamp.isoformat() if log.timestamp else None,
            "bot_probability": log.bot_probability,
        }
        for log in recent_bots
    ]

    return {
        "threats": blocked_ips + bot_threats,
        "total_count": len(blocked_ips) + len(bot_threats),
    }


@router.get("/traffic-chart")
@limiter.limit("60/minute")
def get_traffic_chart(
    request: Request,
    hours: int = 6,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Данные для графика трафика по часам.
    Возвращает массив точек: {hour, total, blocked, bots}
    """
    if hours > 24:
        hours = 24

    now = datetime.utcnow()
    start_time = now - timedelta(hours=hours)

    # Получаем все логи за период
    logs = db.query(RequestLog).filter(RequestLog.timestamp >= start_time).all()

    # Группируем по часам
    hourly_data = {}
    for i in range(hours):
        hour_dt = now - timedelta(hours=hours - i - 1)
        hour_key = hour_dt.strftime("%H:00")
        hourly_data[hour_key] = {"hour": hour_key, "total": 0, "blocked": 0, "bots": 0}

    for log in logs:
        if log.timestamp:
            hour_key = log.timestamp.strftime("%H:00")
            if hour_key in hourly_data:
                hourly_data[hour_key]["total"] += 1
                if log.verdict == "blocked":
                    hourly_data[hour_key]["blocked"] += 1
                if log.is_bot:
                    hourly_data[hour_key]["bots"] += 1

    return {
        "data": list(hourly_data.values()),
        "period_hours": hours,
    }


@router.get("/ml-health")
@limiter.limit("60/minute")
def get_ml_health(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Состояние ML-системы"""
    return {
        "status": "ok",
        "models_loaded": list(predictor.models.keys()),
        "active_model": GLOBAL_RULES["ml_model"],
        "ml_threshold": GLOBAL_RULES["ml_threshold"],
        "available_models": list(predictor.AVAILABLE_MODELS),
    }