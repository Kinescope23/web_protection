import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User, EmailVerificationCode
from app.api.deps import get_current_user
from app.core.email import send_verification_code
from app.core.middleware import limiter
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/api/v1/2fa", tags=["2fa"])


class Enable2FARequest(BaseModel):
    method: str  # "email" или "totp" или "none"


@router.post("/enable-email")
@limiter.limit("5/minute")
async def enable_email_2fa(
    request: Request,
    data: Enable2FARequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Включить/выключить email-2FA"""
    if data.method not in ["none", "email", "totp"]:
        raise HTTPException(400, "Недопустимый метод. Используйте: none, email, totp")

    user.two_factor_method = data.method
    user.is_2fa_enabled = (data.method != "none")
    db.commit()

    return {
        "message": f"2FA метод установлен: {data.method}",
        "method": data.method,
        "is_enabled": user.is_2fa_enabled
    }


@router.post("/send-code")
@limiter.limit("3/minute")
async def send_2fa_code(
    request: Request,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """Отправляет код подтверждения на email после проверки пароля"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(401, "Неверные учетные данные")

    if not verify_password(password, user.password_hash):
        raise HTTPException(401, "Неверные учетные данные")

    if user.two_factor_method != "email":
        raise HTTPException(400, "Email-2FA не включена для этого пользователя")

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    verification = EmailVerificationCode(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
        attempts=0,
        is_used=False
    )
    db.add(verification)
    db.commit()

    success = await send_verification_code(user.email, code, user.username)

    if not success:
        raise HTTPException(500, "Не удалось отправить код. Проверьте настройки SMTP.")

    return {
        "message": "Код отправлен на ваш email",
        "expires_in": 300
    }


@router.post("/verify-code")
@limiter.limit("10/minute")
def verify_2fa_code(
    request: Request,
    email: str,
    code: str,
    db: Session = Depends(get_db)
):
    """Проверяет код и возвращает JWT-токен"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(401, "Неверные учетные данные")

    verification = db.query(EmailVerificationCode).filter(
        EmailVerificationCode.user_id == user.id,
        EmailVerificationCode.is_used == False,
        EmailVerificationCode.expires_at > datetime.utcnow()
    ).order_by(EmailVerificationCode.created_at.desc()).first()

    if not verification:
        raise HTTPException(400, "Код не найден или истёк")

    if verification.attempts >= 3:
        verification.is_used = True
        db.commit()
        raise HTTPException(429, "Превышено количество попыток. Запросите новый код.")

    if verification.code != code:
        verification.attempts += 1
        db.commit()
        remaining = 3 - verification.attempts
        raise HTTPException(400, f"Неверный код. Осталось попыток: {remaining}")

    verification.is_used = True
    db.commit()

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role
        }
    }


@router.get("/status")
def get_2fa_status(
    user: User = Depends(get_current_user)
):
    """Получить статус 2FA"""
    return {
        "is_enabled": user.is_2fa_enabled,
        "method": user.two_factor_method or "none"
    }