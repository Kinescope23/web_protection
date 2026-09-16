import os
import uuid
import math
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Upload, User
from app.api.deps import get_current_user
from app.core.middleware import limiter

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

TMP_DIR = "/app/uploads/tmp"
FINAL_DIR = "/app/uploads/final"
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 ГБ
CHUNK_SIZE = 10 * 1024 * 1024  # 10 МБ


class InitUploadRequest(BaseModel):
    filename: str
    total_size: int
    checksum: str  # SHA-256 всего файла


class InitUploadResponse(BaseModel):
    upload_id: str
    chunk_size: int
    total_chunks: int


@router.post("/init", response_model=InitUploadResponse)
@limiter.limit("20/minute")
def init_upload(
    request: Request,
    data: InitUploadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Инициализация загрузки большого файла.
    Возвращает upload_id и информацию о том, как разбить файл на чанки.
    """
    if data.total_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"Файл слишком большой. Максимум: {MAX_FILE_SIZE // (1024**3)} ГБ")

    if data.total_size <= 0:
        raise HTTPException(400, "Размер файла должен быть больше 0")

    total_chunks = math.ceil(data.total_size / CHUNK_SIZE)
    upload_id = str(uuid.uuid4())

    upload = Upload(
        id=upload_id,
        user_id=user.id,
        filename=data.filename,
        total_size=data.total_size,
        chunk_size=CHUNK_SIZE,
        total_chunks=total_chunks,
        uploaded_chunks=0,
        checksum=data.checksum,
        status="in_progress"
    )
    db.add(upload)
    db.commit()

    # Создаём директорию для чанков
    os.makedirs(os.path.join(TMP_DIR, upload_id), exist_ok=True)

    return InitUploadResponse(
        upload_id=upload_id,
        chunk_size=CHUNK_SIZE,
        total_chunks=total_chunks
    )


@router.post("/chunk")
@limiter.limit("120/minute")
async def upload_chunk(
    request: Request,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загрузка одного чанка файла.
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Загрузка не найдена")
    if upload.user_id != user.id:
        raise HTTPException(403, "Доступ запрещён")
    if upload.status != "in_progress":
        raise HTTPException(400, f"Загрузка в статусе '{upload.status}'")

    if chunk_index < 0 or chunk_index >= upload.total_chunks:
        raise HTTPException(400, f"Неверный индекс чанка. Допустимо: 0-{upload.total_chunks - 1}")

    # Читаем содержимое чанка
    content = await file.read()
    expected_size = CHUNK_SIZE if chunk_index < upload.total_chunks - 1 else (
        upload.total_size - (upload.total_chunks - 1) * CHUNK_SIZE
    )
    if len(content) != expected_size:
        raise HTTPException(400, f"Неверный размер чанка. Ожидалось: {expected_size}, получено: {len(content)}")

    # Сохраняем чанк
    chunk_path = os.path.join(TMP_DIR, upload_id, f"chunk_{chunk_index:06d}")
    with open(chunk_path, "wb") as f:
        f.write(content)

    # Обновляем счётчик загруженных чанков
    upload.uploaded_chunks += 1
    db.commit()

    return {
        "message": "Чанк загружен",
        "chunk_index": chunk_index,
        "uploaded_chunks": upload.uploaded_chunks,
        "total_chunks": upload.total_chunks,
        "progress": round((upload.uploaded_chunks / upload.total_chunks) * 100, 2)
    }


@router.post("/complete")
@limiter.limit("20/minute")
def complete_upload(
    request: Request,
    upload_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Завершение загрузки: сборка чанков в финальный файл и проверка SHA-256.
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Загрузка не найдена")
    if upload.user_id != user.id:
        raise HTTPException(403, "Доступ запрещён")
    if upload.status != "in_progress":
        raise HTTPException(400, f"Загрузка уже в статусе '{upload.status}'")

    if upload.uploaded_chunks != upload.total_chunks:
        raise HTTPException(
            400,
            f"Не все чанки загружены. Загружено: {upload.uploaded_chunks}/{upload.total_chunks}"
        )

    # Собираем финальный файл
    final_filename = f"{upload.id}_{upload.filename}"
    final_path = os.path.join(FINAL_DIR, final_filename)
    sha256 = hashlib.sha256()

    try:
        with open(final_path, "wb") as out_f:
            for i in range(upload.total_chunks):
                chunk_path = os.path.join(TMP_DIR, upload_id, f"chunk_{i:06d}")
                if not os.path.exists(chunk_path):
                    raise HTTPException(500, f"Чанк {i} не найден")
                with open(chunk_path, "rb") as in_f:
                    while chunk := in_f.read(8192):
                        out_f.write(chunk)
                        sha256.update(chunk)
    except Exception as e:
        upload.status = "failed"
        db.commit()
        raise HTTPException(500, f"Ошибка сборки файла: {str(e)}")

    # Проверяем контрольную сумму
    actual_checksum = sha256.hexdigest()
    if actual_checksum != upload.checksum:
        # Удаляем повреждённый файл
        try:
            os.remove(final_path)
        except OSError:
            pass
        upload.status = "failed"
        db.commit()
        raise HTTPException(
            400,
            f"Контрольная сумма не совпадает. Ожидалось: {upload.checksum}, получено: {actual_checksum}"
        )

    # Удаляем временные чанки
    import shutil
    try:
        shutil.rmtree(os.path.join(TMP_DIR, upload_id))
    except OSError:
        pass

    # Обновляем статус
    upload.status = "completed"
    upload.completed_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Файл успешно загружен",
        "upload_id": upload_id,
        "filename": upload.filename,
        "size": upload.total_size,
        "checksum": actual_checksum,
        "path": f"/uploads/final/{final_filename}"
    }


@router.get("/status/{upload_id}")
def get_upload_status(
    upload_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статус загрузки"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Загрузка не найдена")
    if upload.user_id != user.id:
        raise HTTPException(403, "Доступ запрещён")

    return {
        "upload_id": upload.id,
        "filename": upload.filename,
        "total_size": upload.total_size,
        "total_chunks": upload.total_chunks,
        "uploaded_chunks": upload.uploaded_chunks,
        "progress": round((upload.uploaded_chunks / upload.total_chunks) * 100, 2) if upload.total_chunks > 0 else 0,
        "status": upload.status,
        "checksum": upload.checksum,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "completed_at": upload.completed_at.isoformat() if upload.completed_at else None
    }