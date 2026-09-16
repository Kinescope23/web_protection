from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, InvitationKey, AuditLog
from app.api.deps import get_current_user
from app.api.metrics import GLOBAL_RULES
import secrets
from datetime import datetime
from app.ml import predictor

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# === Зависимость для проверки роли администратора ===
def require_admin(user: User = Depends(get_current_user)) -> User:
    """Проверяет, что текущий пользователь является администратором"""
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Доступ запрещен. Требуются права администратора."
        )
    return user


def log_audit(db: Session, user_id: int, action: str, details: str, ip: str):
    """Логирование действий администратора"""
    audit = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.add(audit)
    db.commit()


@router.post("/generate-invite")
def generate_invite_key(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Генерация уникального ключа приглашения для регистрации нового пользователя.
    """
    new_key = f"NP-{secrets.token_urlsafe(16).upper()}"

    invite = InvitationKey(key=new_key, created_by=admin.id, is_used=False)
    db.add(invite)

    log_audit(
        db,
        admin.id,
        "GENERATE_INVITE",
        f"Создан ключ регистрации: {new_key}",
        request.client.host,
    )
    db.commit()

    return {"invitation_key": new_key, "message": "Ключ успешно создан"}


@router.get("/invitation-keys")
def get_invitation_keys(
    admin: User = Depends(require_admin), db: Session = Depends(get_db), limit: int = 50
):
    """Получить список всех ключей приглашения"""
    keys = (
        db.query(InvitationKey)
        .order_by(InvitationKey.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": key.id,
            "key": key.key,
            "is_used": key.is_used,
            "created_at": key.created_at.isoformat(),
            "created_by": key.created_by,
        }
        for key in keys
    ]


@router.post("/ml-settings")
def update_ml_settings(
    request: Request,
    threshold: float,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Обновление порога чувствительности ML-модели.
    Доступно только администраторам.
    """
    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(400, "Порог чувствительности должен быть от 0.0 до 1.0")

    old_threshold = GLOBAL_RULES["ml_threshold"]
    GLOBAL_RULES["ml_threshold"] = threshold
    GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

    log_audit(
        db,
        admin.id,
        "UPDATE_ML_SETTINGS",
        f"Изменен порог ML-анализа с {old_threshold} на {threshold}",
        request.client.host,
    )

    return {"message": "Настройки ML обновлены", "new_threshold": threshold}


@router.get("/audit-logs")
def get_audit_logs(
    admin: User = Depends(require_admin), db: Session = Depends(get_db), limit: int = 50
):
    """Получить список последних действий администраторов"""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]

@router.get("/ml-models")
def get_available_models(
    admin: User = Depends(require_admin)
):
    """Получить список доступных ML-моделей и их статус"""
    available = list(predictor.AVAILABLE_MODELS)
    loaded = list(predictor.models.keys())

    return {
        "available_models": available,
        "loaded_models": loaded,
        "active_model": GLOBAL_RULES["ml_model"],
        "models_info": [
            {
                "name": name,
                "status": "loaded" if name in loaded else "not_loaded",
                "is_active": name == GLOBAL_RULES["ml_model"]
            }
            for name in available
        ]
    }


@router.post("/ml-model/active")
def set_active_model(
    request: Request,
    model_name: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Установить активную ML-модель"""
    if model_name not in predictor.AVAILABLE_MODELS:
        raise HTTPException(
            400,
            f"Неизвестная модель. Доступны: {', '.join(predictor.AVAILABLE_MODELS)}"
        )

    if model_name not in predictor.models:
        raise HTTPException(
            400,
            f"Модель '{model_name}' не загружена на сервере"
        )

    old_model = GLOBAL_RULES["ml_model"]
    GLOBAL_RULES["ml_model"] = model_name
    GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

    log_audit(
        db, admin.id, "CHANGE_ML_MODEL",
        f"Изменена активная ML-модель с '{old_model}' на '{model_name}'",
        request.client.host
    )

    return {
        "message": f"Активная модель изменена на '{model_name}'",
        "previous_model": old_model,
        "current_model": model_name
    }

@router.get("/stats")
def get_system_stats(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Получение общей статистики системы для дашборда администратора"""
    total_users = db.query(User).count()
    active_invites = (
        db.query(InvitationKey).filter(InvitationKey.is_used == False).count()
    )

    return {
        "total_users": total_users,
        "active_invitation_keys": active_invites,
        "current_ml_threshold": GLOBAL_RULES["ml_threshold"],
        "currently_blocked_ips": len(GLOBAL_RULES["block_ips"]),
    }

@router.get("/ml-models")
def get_available_models(
    admin: User = Depends(require_admin)
):
    """
    Получить список доступных ML-моделей и их статус загрузки.
    """
    available = list(predictor.AVAILABLE_MODELS)
    loaded = list(predictor.models.keys())

    return {
        "available_models": available,
        "loaded_models": loaded,
        "active_model": GLOBAL_RULES["ml_model"],
        "models_info": [
            {
                "name": name,
                "status": "loaded" if name in loaded else "not_loaded",
                "is_active": name == GLOBAL_RULES["ml_model"]
            }
            for name in available
        ]
    }

@router.post("/ml-model/active")
def set_active_model(
    request: Request,
    model_name: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Установить активную ML-модель для анализа трафика.
    Модель должна быть загружена на сервере.
    """
    # Валидация: модель должна быть в списке доступных
    if model_name not in predictor.AVAILABLE_MODELS:
        raise HTTPException(
            400,
            f"Неизвестная модель. Доступны: {', '.join(predictor.AVAILABLE_MODELS)}"
        )

    # Валидация: модель должна быть загружена
    if model_name not in predictor.models:
        raise HTTPException(
            400,
            f"Модель '{model_name}' не загружена на сервере. "
            f"Загружены: {', '.join(predictor.models.keys()) or 'нет'}"
        )

    old_model = GLOBAL_RULES["ml_model"]
    GLOBAL_RULES["ml_model"] = model_name
    GLOBAL_RULES["updated_at"] = datetime.utcnow().isoformat()

    log_audit(
        db, admin.id, "CHANGE_ML_MODEL",
        f"Изменена активная ML-модель с '{old_model}' на '{model_name}'",
        request.client.host
    )

    return {
        "message": f"Активная модель изменена на '{model_name}'",
        "previous_model": old_model,
        "current_model": model_name
    }
