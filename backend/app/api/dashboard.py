from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, RequestLog, Agent, UserMLSettings
from app.api.deps import get_current_user
from app.core.middleware import limiter
from app.ml import predictor
from fastapi import APIRouter, Depends, HTTPException, Request, Query

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/users")
@limiter.limit("60/minute")
def get_users_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список пользователей с агентами (для админа) или только себя (для пользователя)"""
    if user.role == "admin":
        users = db.query(User).all()
    else:
        users = [user]

    result = []
    for u in users:
        agents = db.query(Agent).filter(Agent.user_id == u.id).all()
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)

        agent_ids = [a.agent_id for a in agents]
        total_requests = 0
        blocked = 0
        bots = 0

        if agent_ids:
            logs = (
                db.query(RequestLog)
                .filter(
                    RequestLog.agent_id.in_(agent_ids),
                    RequestLog.timestamp >= last_hour,
                )
                .all()
            )
            total_requests = len(logs)
            blocked = sum(1 for l in logs if l.verdict == "blocked")
            bots = sum(1 for l in logs if l.is_bot)

        settings = (
            db.query(UserMLSettings).filter(UserMLSettings.user_id == u.id).first()
        )

        result.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "agents_count": len(agents),
                "agents": [
                    {
                        "agent_id": a.agent_id,
                        "name": a.name,
                        "domain": a.domain,
                        "is_active": a.is_active,
                        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
                    }
                    for a in agents
                ],
                "last_hour": {
                    "total_requests": total_requests,
                    "blocked": blocked,
                    "bots": bots,
                },
                "ml_model": settings.ml_model if settings else "isolation_forest",
                "ml_threshold": settings.ml_threshold if settings else 0.65,
            }
        )

    return result


@router.get("/user/{user_id}")
@limiter.limit("60/minute")
def get_user_metrics(
    request: Request,
    user_id: int,
    # ИСПРАВЛЕНИЕ: Жесткая валидация входных данных (ge=1, le=24)
    hours: int = Query(default=6, ge=1, le=24, description="Количество часов от 1 до 24"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Метрики конкретного пользователя"""
    if user.role != "admin" and user.id != user_id:
        raise HTTPException(403, "Доступ запрещён")
    hours = max(1, min(int(hours), 24))
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "Пользователь не найден")

    agents = db.query(Agent).filter(Agent.user_id == user_id).all()
    agent_ids = [a.agent_id for a in agents]

    now = datetime.utcnow()
    start_time = now - timedelta(hours=hours)
    last_hour = now - timedelta(hours=1)

    if not agent_ids:
        return {
            "user": {"id": target.id, "username": target.username, "email": target.email, "role": target.role},
            "agents": [],
            "stats": {"total": 0, "blocked": 0, "bots": 0, "avg_bot_prob": 0},
            "traffic_chart": [],
            "recent_logs": [],
            "threats": [],
            "risk_distribution": {"low": 0, "medium": 0, "high": 0}
        }

    # Статистика за последний час
    hour_logs = db.query(RequestLog).filter(
        RequestLog.agent_id.in_(agent_ids),
        RequestLog.timestamp >= last_hour
    ).all()

    total = len(hour_logs)
    blocked = sum(1 for l in hour_logs if l.verdict == "blocked")
    bots = sum(1 for l in hour_logs if l.is_bot)
    probs = [l.bot_probability for l in hour_logs if l.bot_probability is not None]
    avg_prob = sum(probs) / len(probs) if probs else 0

    # Распределение риска
    risk_dist = {"low": 0, "medium": 0, "high": 0}
    for l in hour_logs:
        if l.risk_level in risk_dist:
            risk_dist[l.risk_level] += 1

    # График трафика
    all_logs = db.query(RequestLog).filter(
        RequestLog.agent_id.in_(agent_ids),
        RequestLog.timestamp >= start_time
    ).all()

    hourly = {}
    # 🔥 Теперь SAST знает, что hours гарантированно <= 24
    for i in range(hours):
        h = (now - timedelta(hours=hours - i - 1)).strftime("%H:00")
        hourly[h] = {"hour": h, "total": 0, "blocked": 0, "bots": 0}

    for l in all_logs:
        if l.timestamp:
            h = l.timestamp.strftime("%H:00")
            if h in hourly:
                hourly[h]["total"] += 1
                if l.verdict == "blocked":
                    hourly[h]["blocked"] += 1
                if l.is_bot:
                    hourly[h]["bots"] += 1

    # Последние логи
    recent = db.query(RequestLog).filter(
        RequestLog.agent_id.in_(agent_ids)
    ).order_by(desc(RequestLog.timestamp)).limit(20).all()

    # Угрозы
    bot_logs = db.query(RequestLog).filter(
        RequestLog.agent_id.in_(agent_ids),
        RequestLog.is_bot == True,
        RequestLog.timestamp >= last_hour
    ).order_by(desc(RequestLog.timestamp)).limit(10).all()

    settings = db.query(UserMLSettings).filter(UserMLSettings.user_id == user_id).first()

    return {
        "user": {"id": target.id, "username": target.username, "email": target.email, "role": target.role},
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "domain": a.domain,
                "is_active": a.is_active,
                "last_seen": a.last_seen.isoformat() if a.last_seen else None
            }
            for a in agents
        ],
        "ml_settings": {
            "model": settings.ml_model if settings else "isolation_forest",
            "threshold": settings.ml_threshold if settings else 0.65
        },
        "stats": {
            "total": total,
            "blocked": blocked,
            "bots": bots,
            "avg_bot_prob": round(avg_prob, 4)
        },
        "risk_distribution": risk_dist,
        "traffic_chart": list(hourly.values()),
        "recent_logs": [
            {
                "id": l.id,
                "agent_id": l.agent_id,
                "src_ip": l.src_ip,
                "verdict": l.verdict,
                "bot_probability": l.bot_probability,
                "risk_level": l.risk_level,
                "is_bot": l.is_bot,
                "ml_model_used": l.ml_model_used,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None
            }
            for l in recent
        ],
        "threats": [
            {
                "value": l.src_ip,
                "severity": l.risk_level or "medium",
                "bot_probability": l.bot_probability,
                "detected_at": l.timestamp.isoformat() if l.timestamp else None
            }
            for l in bot_logs
        ]
    }
