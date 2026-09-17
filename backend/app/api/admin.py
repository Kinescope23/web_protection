from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, InvitationKey, AuditLog, Agent, UserMLSettings
from app.api.deps import get_current_user
from app.api.metrics import GLOBAL_RULES
from app.ml import predictor
import secrets
import os
from datetime import datetime
import aiofiles
from werkzeug.utils import secure_filename

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

BASE_DIR = "/app/ml_models"


# === Зависимость для проверки роли администратора ===
def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Доступ запрещен. Требуются права администратора."
        )
    return user


def log_audit(db: Session, user_id: int, action: str, details: str, ip: str):
    audit = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.add(audit)
    db.commit()


# === Ключи приглашения ===


@router.post("/generate-invite")
def generate_invite_key(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
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


# === ML-модели (только просмотр и управление файлами) ===


@router.get("/ml-models")
def get_available_models(admin: User = Depends(require_admin)):
    """Получить список доступных ML-моделей и их статус загрузки"""
    available = list(predictor.AVAILABLE_MODELS)
    loaded = list(predictor.models.keys())

    return {
        "available_models": available,
        "loaded_models": loaded,
        "models_info": [
            {"name": name, "status": "loaded" if name in loaded else "not_loaded"}
            for name in available
        ],
    }


@router.post("/ml-models")
async def upload_ml_model(
        model_file: UploadFile = File(...),
        scaler_file: UploadFile = File(...),
        admin: User = Depends(require_admin)
):
    # 1. Санитизация имен файлов (защита от Path Traversal)
    safe_model_name = secure_filename(model_file.filename)
    safe_scaler_name = secure_filename(scaler_file.filename)

    if not safe_model_name.endswith(".pkl") or safe_model_name.endswith("_scaler.pkl"):
        raise HTTPException(400, "Файл модели должен иметь расширение .pkl и не быть скейлером")
    if not safe_scaler_name.endswith("_scaler.pkl"):
        raise HTTPException(400, "Файл скейлера должен иметь расширение _scaler.pkl")

    model_name = safe_model_name[:-4]
    expected_scaler_name = f"{model_name}_scaler.pkl"

    if safe_scaler_name != expected_scaler_name:
        raise HTTPException(400, f"Имя файла скейлера должно быть {expected_scaler_name}")

    os.makedirs(BASE_DIR, exist_ok=True)
    model_path = os.path.join(BASE_DIR, safe_model_name)
    scaler_path = os.path.join(BASE_DIR, safe_scaler_name)

    # 2. Асинхронная запись файлов (исправление SAST предупреждения)
    async with aiofiles.open(model_path, "wb") as f:
        await f.write(await model_file.read())
    async with aiofiles.open(scaler_path, "wb") as f:
        await f.write(await scaler_file.read())

    predictor._load_all()

    return {"message": f"Модель '{model_name}' успешно загружена и активирована"}


@router.delete("/ml-models/{model_name}")
def delete_ml_model(
    model_name: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Удалить ML-модель с сервера"""
    if model_name not in predictor.models:
        raise HTTPException(404, "Модель не найдена")

    model_path = os.path.join(BASE_DIR, f"{model_name}.pkl")
    scaler_path = os.path.join(BASE_DIR, f"{model_name}_scaler.pkl")

    try:
        os.remove(model_path)
        os.remove(scaler_path)
    except OSError as e:
        raise HTTPException(500, f"Ошибка удаления файлов модели: {str(e)}")

    predictor._load_all()

    log_audit(
        db,
        admin.id,
        "DELETE_ML_MODEL",
        f"Удалена модель: {model_name}",
        request.client.host if request.client else "unknown",
    )

    return {"message": f"Модель '{model_name}' успешно удалена"}


# === Управление агентами ===


@router.get("/agents")
def get_all_agents(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Получить список всех агентов"""
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "agent_id": a.agent_id,
            "user_id": a.user_id,
            "username": a.user.username if a.user else "неизвестно",
            "name": a.name,
            "domain": a.domain,
            "is_active": a.is_active,
            "last_seen": a.last_seen.isoformat() if a.last_seen else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in agents
    ]


@router.post("/agents")
def create_agent(
    request: Request,
    agent_id: str,
    user_id: int,
    name: str,
    domain: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Создать нового агента для пользователя"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "Пользователь не найден")

    existing = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if existing:
        raise HTTPException(400, "Агент с таким ID уже существует")

    agent = Agent(
        agent_id=agent_id,
        user_id=user_id,
        name=name,
        domain=domain or None,
        is_active=True,
    )
    db.add(agent)

    log_audit(
        db,
        admin.id,
        "CREATE_AGENT",
        f"Создан агент: {agent_id} для user_id={user_id}",
        request.client.host,
    )
    db.commit()

    return {"message": "Агент создан", "agent_id": agent_id}


@router.delete("/agents/{agent_db_id}")
def delete_agent(
    agent_db_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Удалить агента"""
    agent = db.query(Agent).filter(Agent.id == agent_db_id).first()
    if not agent:
        raise HTTPException(404, "Агент не найден")

    log_audit(
        db,
        admin.id,
        "DELETE_AGENT",
        f"Удалён агент: {agent.agent_id} (user_id={agent.user_id})",
        request.client.host if request.client else "unknown",
    )

    db.delete(agent)
    db.commit()
    return {"message": f"Агент '{agent.agent_id}' удалён"}


# === Per-user ML настройки ===


@router.post("/user/{user_id}/ml-settings")
def set_user_ml_settings(
    request: Request,
    user_id: int,
    ml_model: str,
    threshold: float,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Установить ML-настройки для конкретного пользователя"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "Пользователь не найден")

    if ml_model not in predictor.models:
        raise HTTPException(400, f"Модель '{ml_model}' не загружена")

    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(400, "Порог должен быть от 0.0 до 1.0")

    settings = (
        db.query(UserMLSettings).filter(UserMLSettings.user_id == user_id).first()
    )
    if not settings:
        settings = UserMLSettings(
            user_id=user_id, ml_model=ml_model, ml_threshold=threshold
        )
        db.add(settings)
    else:
        settings.ml_model = ml_model
        settings.ml_threshold = threshold
        settings.updated_at = datetime.utcnow()

    log_audit(
        db,
        admin.id,
        "UPDATE_USER_ML",
        f"ML для user={user_id}: model={ml_model}, threshold={threshold}",
        request.client.host,
    )
    db.commit()

    return {
        "message": "Настройки ML обновлены",
        "ml_model": ml_model,
        "ml_threshold": threshold,
    }


# === Статистика и аудит ===


@router.get("/audit-logs")
def get_audit_logs(
    admin: User = Depends(require_admin), db: Session = Depends(get_db), limit: int = 50
):
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


@router.get("/stats")
def get_system_stats(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Общая статистика системы"""
    total_users = db.query(User).count()
    active_invites = (
        db.query(InvitationKey).filter(InvitationKey.is_used == False).count()
    )
    total_agents = db.query(Agent).count()

    return {
        "total_users": total_users,
        "active_invitation_keys": active_invites,
        "currently_blocked_ips": len(GLOBAL_RULES["block_ips"]),
        "total_agents": total_agents,
        "loaded_ml_models": list(predictor.models.keys()),
    }
