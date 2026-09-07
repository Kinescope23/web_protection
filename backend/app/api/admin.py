from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, InvitationKey, AuditLog
from app.api.metrics import GLOBAL_RULES
from app.core.security import hash_password  # Если понадобится сброс пароля
import secrets
from datetime import datetime

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# === Зависимость для проверки роли администратора ===
def require_admin(user: User = Depends(lambda: None)):  # Замените lambda на реальный get_current_user из deps.py
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуются права администратора.")
    return user


def log_audit(db: Session, user_id: int, action: str, details: str, ip: str):
    """Вспомогательная функция для логирования действий (ТРЕБОВАНИЕ: Все действия пользователя логируются)"""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip
    )
    db.add(audit)
    db.commit()


@router.post("/generate-invite")
def generate_invite_key(
        request: Request,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    ТРЕБОВАНИЕ: Регистрация новых пользователей происходит по уникальному ключу,
    указанному администратором.
    """
    new_key = f"NP-{secrets.token_urlsafe(16).upper()}"

    invite = InvitationKey(
        key=new_key,
        created_by=admin.id,
        is_used=False
    )
    db.add(invite)

    log_audit(db, admin.id, "GENERATE_INVITE", f"Создан ключ регистрации: {new_key}", request.client.host)
    db.commit()

    return {"invitation_key": new_key, "message": "Ключ успешно создан"}


@router.post("/ml-settings")
def update_ml_settings(
        request: Request,
        threshold: float,
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    ТРЕБОВАНИЕ: Настройки ML-модели (порог чувствительности) вынесены в расширенный режим
    и доступны только администраторам.
    """
    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(400, "Порог чувствительности должен быть от 0.0 до 1.0")

    old_threshold = GLOBAL_RULES["ml_threshold"]
    GLOBAL_RULES["ml_threshold"] = threshold
    GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

    log_audit(
        db, admin.id, "UPDATE_ML_SETTINGS",
        f"Изменен порог ML-анализа с {old_threshold} на {threshold}",
        request.client.host
    )

    return {"message": "Настройки ML обновлены", "new_threshold": threshold}


@router.get("/audit-logs")
def get_audit_logs(
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db),
        limit: int = 50
):
    """
    ТРЕБОВАНИЕ: Все действия пользователя логируются.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]


@router.get("/stats")
def get_system_stats(
        admin: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """Получение общей статистики для дашборда администратора"""
    total_users = db.query(User).count()
    active_invites = db.query(InvitationKey).filter(InvitationKey.is_used == False).count()

    return {
        "total_users": total_users,
        "active_invitation_keys": active_invites,
        "current_ml_threshold": GLOBAL_RULES["ml_threshold"],
        "currently_blocked_ips": len(GLOBAL_RULES["block_ips"])
    }