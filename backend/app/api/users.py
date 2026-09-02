from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Session as SessionModel, APIToken
from app.schemas import UserResponse, ChangePassword, APITokenCreate
from app.core.security import verify_password, hash_password
from app.api.deps import get_current_user
import hashlib, secrets, os

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/password")
def change_password(data: ChangePassword, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Неверный текущий пароль")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Пароль успешно изменен"}


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(415, "Допустимы только изображения")

    # В реальном проекте здесь будет сохранение в S3 или на диск
    user.avatar_url = f"https://via.placeholder.com/150?text={user.username}"
    db.commit()
    return {"avatar_url": user.avatar_url}


@router.get("/me/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(SessionModel).filter(SessionModel.user_id == user.id, SessionModel.is_active == True).all()
    return [{"id": s.id[:8] + "...", "ip": s.ip_address, "created": s.created_at} for s in sessions]


@router.post("/me/sessions/revoke-all")
def revoke_all_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(SessionModel).filter(SessionModel.user_id == user.id).update({"is_active": False})
    db.commit()
    return {"message": "Все сессии завершены"}


# Управление API токенами
@router.get("/me/tokens")
def list_tokens(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tokens = db.query(APIToken).filter(APIToken.user_id == user.id, APIToken.is_active == True).all()
    return [{"id": t.id, "name": t.name, "scopes": t.scopes, "created": t.created_at} for t in tokens]


@router.post("/me/tokens")
def create_token(data: APITokenCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw_token = f"np_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = APIToken(user_id=user.id, name=data.name, token_hash=token_hash, scopes=",".join(data.scopes or []))
    db.add(token)
    db.commit()
    return {"id": token.id, "name": token.name, "token": raw_token,
            "warning": "Сохраните токен, он не будет показан снова!"}