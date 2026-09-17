import os
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image
import aiofiles
from pathlib import Path

from app.database import get_db
from app.models import User, Session as SessionModel, APIToken
from app.schemas import UserResponse
from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.core.middleware import limiter

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# === Получение текущего пользователя ===
@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


# === Смена пароля ===
class ChangePasswordRequest:
    pass


from pydantic import BaseModel, Field


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/me/password")
@limiter.limit("5/hour")
def change_password(
    request: Request,
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Смена пароля с обязательной проверкой текущего пароля.
    После смены пароля все сессии кроме текущей завершаются.
    """
    # Проверка текущего пароля
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Неверный текущий пароль")

    # Обновление пароля
    user.password_hash = hash_password(data.new_password)

    # Завершаем все сессии кроме текущей (для безопасности)
    current_session_id = request.headers.get("x-session-id")
    if current_session_id:
        db.query(SessionModel).filter(
            SessionModel.user_id == user.id, SessionModel.id != current_session_id
        ).update({"is_active": False})

    db.commit()

    return {"message": "Пароль успешно изменён. Все другие сессии завершены."}


# === Список активных сессий ===
@router.get("/me/sessions")
def get_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список активных сессий пользователя"""
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == user.id,
            SessionModel.is_active == True,
            SessionModel.expires_at > datetime.utcnow(),
        )
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "is_current": False,  # Будет обновлено ниже
        }
        for s in sessions
    ]


# === Завершение одной сессии ===
@router.delete("/me/sessions/{session_id}")
def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Завершить конкретную сессию"""
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.user_id == user.id)
        .first()
    )

    if not session:
        raise HTTPException(404, "Сессия не найдена")

    session.is_active = False
    db.commit()

    return {"message": "Сессия завершена"}


# === Завершение всех сессий кроме текущей ===
@router.delete("/me/sessions")
def revoke_all_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Завершить все сессии кроме текущей"""
    current_session_id = request.headers.get("x-session-id")

    query = db.query(SessionModel).filter(
        SessionModel.user_id == user.id, SessionModel.is_active == True
    )

    if current_session_id:
        query = query.filter(SessionModel.id != current_session_id)

    count = query.update({"is_active": False})
    db.commit()

    return {"message": f"Завершено сессий: {count}"}


# === Смена аватара ===
AVATARS_DIR = "/app/uploads/avatars"
os.makedirs(AVATARS_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5 МБ


@router.post("/me/avatar")
@limiter.limit("10/hour")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Загрузка аватара пользователя"""
    # Валидация типа
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            415, f"Неподдерживаемый тип файла. Разрешены: {', '.join(ALLOWED_TYPES)}"
        )

    # Читаем содержимое
    content = await file.read()

    # Валидация размера
    if len(content) > MAX_SIZE:
        raise HTTPException(
            413, f"Файл слишком большой. Максимум: {MAX_SIZE // (1024*1024)} МБ"
        )

    # Валидация через PIL (защита от подмены расширения)
    try:
        from io import BytesIO

        img = Image.open(BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(415, "Файл не является валидным изображением")

    # Удаляем старый аватар, если есть
    if user.avatar_url:
        old_path = os.path.join("/app", user.avatar_url.lstrip("/"))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    # Сохраняем новый аватар с уникальным именем
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        ext = "jpg"
    filename = f"{user.id}_{secrets.token_hex(8)}.{ext}"
    filepath = os.path.join(AVATARS_DIR, filename)

    # Асинхронная запись
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    # Обновляем запись в БД
    user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(user)

    return {"message": "Аватар успешно загружен", "avatar_url": user.avatar_url}


# === Получение аватара ===
@router.get("/me/avatar")
def get_avatar(user: User = Depends(get_current_user)):
    """Получить аватар текущего пользователя"""
    if not user.avatar_url:
        raise HTTPException(404, "Аватар не установлен")

    filepath = os.path.join("/app", user.avatar_url.lstrip("/"))
    if not os.path.exists(filepath):
        raise HTTPException(404, "Файл аватара не найден")

    return FileResponse(filepath)


# === Публичный эндпоинт для получения аватара по URL ===
@router.get("/avatar/{filename}")
def get_avatar_public(filename: str):
    # 1. Базовая санитизация
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Недопустимое имя файла")

    # 2. Проверка расширения
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        raise HTTPException(400, "Недопустимое расширение файла")

    # 3. Защита от Path Traversal через разрешение абсолютного пути
    avatars_dir = Path("/app/uploads/avatars").resolve()
    filepath = (avatars_dir / filename).resolve()

    # 4. Проверка, что путь находится строго внутри разрешенной директории (исправление Filesystem Oracle)
    if not str(filepath).startswith(str(avatars_dir)):
        raise HTTPException(403, "Доступ запрещен")

    if not filepath.exists():
        raise HTTPException(404, "Аватар не найден")

    return FileResponse(str(filepath))
