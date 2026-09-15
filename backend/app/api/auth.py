from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app.models import User, Session as SessionModel, InvitationKey
from app.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.middleware import limiter
from app.api.deps import get_current_user

import os
import uuid
import pyotp
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# === Мастер-ключ для регистрации администраторов ===
MASTER_INVITE_KEY = os.getenv("MASTER_INVITE_KEY", "NP-MASTER-2026-SUPER-ADMIN")
MASTER_INVITE_MAX_USES = int(os.getenv("MASTER_INVITE_MAX_USES", "-1"))

# Счетчик использований мастер-ключа (в памяти; в продакшене хранить в БД)
_master_key_uses = 0

# === Инициализация OAuth ===
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="github",
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


# === Регистрация ===
@router.post("/register", response_model=UserResponse)
@limiter.limit("5/hour")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.

    Логика ключей:
    - Если invitation_key == MASTER_INVITE_KEY -> пользователь получает роль 'admin'
    - Иначе ключ ищется в таблице invitation_keys -> роль 'user'
    """
    global _master_key_uses

    # 1. Определяем роль по ключу
    role = "user"
    is_master_key = False

    if data.invitation_key == MASTER_INVITE_KEY:
        # Проверка лимита использований мастер-ключа
        if MASTER_INVITE_MAX_USES != -1 and _master_key_uses >= MASTER_INVITE_MAX_USES:
            raise HTTPException(
                403,
                f"Мастер-ключ достиг лимита использований ({MASTER_INVITE_MAX_USES})",
            )
        role = "admin"
        is_master_key = True
    else:
        # Обычный одноразовый ключ из БД
        invite = (
            db.query(InvitationKey)
            .filter(
                InvitationKey.key == data.invitation_key, InvitationKey.is_used == False
            )
            .first()
        )

        if not invite:
            raise HTTPException(
                403,
                "Недействительный или уже использованный ключ регистрации. "
                "Получите ключ у администратора.",
            )

    # 2. Проверка уникальности email и username
    if (
        db.query(User)
        .filter(or_(User.email == data.email, User.username == data.username))
        .first()
    ):
        raise HTTPException(400, "Email или username уже заняты")

    # 3. Создание пользователя
    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        role=role,
    )
    db.add(user)

    # 4. Помечаем ключ как использованный (только для обычных ключей)
    if not is_master_key:
        invite.is_used = True
    else:
        _master_key_uses += 1

    db.commit()
    db.refresh(user)

    return user


# === Вход ===
@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверные учетные данные")
    if not user.is_active:
        raise HTTPException(403, "Аккаунт заблокирован")

    # Проверка 2FA
    if user.is_2fa_enabled:
        if not data.totp_code or not pyotp.TOTP(user.totp_secret).verify(
            data.totp_code
        ):
            raise HTTPException(401, "Неверный код 2FA")

    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        user_id=user.id,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(session)
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "session_id": session_id})
    return {"access_token": access_token, "token_type": "bearer"}


# === OAuth: начало входа ===
@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Перенаправление на провайдера OAuth"""
    if provider not in ["google", "github"]:
        raise HTTPException(400, "Неподдерживаемый провайдер OAuth")

    # Явно используем FRONTEND_URL, чтобы гарантировать https:// вместо http://
    frontend_url = os.getenv("FRONTEND_URL", "https://localhost")
    redirect_uri = f"{frontend_url}/api/v1/auth/oauth/{provider}/callback"

    return await getattr(oauth, provider).authorize_redirect(request, redirect_uri)


# === OAuth: callback от провайдера ===
@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str, request: Request, db: Session = Depends(get_db)
):
    """Обработка callback от провайдера OAuth"""
    try:
        token = await getattr(oauth, provider).authorize_access_token(request)

        # Получаем данные пользователя
        if provider == "google":
            userinfo = token.get("userinfo", {})
            email = userinfo.get("email")
            username = userinfo.get("name", email.split("@")[0] if email else "user")
        else:  # github
            resp = await getattr(oauth, provider).get("user", token=token)
            userinfo = resp.json()
            email = userinfo.get("email")
            username = userinfo.get("login", "user")

            # Если email не публичный, получаем его отдельно
            if not email:
                resp = await getattr(oauth, provider).get("user/emails", token=token)
                emails = resp.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                email = (
                    primary_email.get("email")
                    if primary_email
                    else f"{username}@github.local"
                )

        if not email:
            raise HTTPException(400, "Не удалось получить email от провайдера")

        # Проверяем, существует ли пользователь
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Создаем нового пользователя (роль 'user' по умолчанию)
            user = User(
                email=email,
                username=username,
                password_hash="",  # OAuth пользователи не имеют пароля
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Создаем сессию и JWT-токен
        session_id = str(uuid.uuid4())
        session = SessionModel(
            id=session_id,
            user_id=user.id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(session)
        db.commit()

        access_token = create_access_token(
            {"sub": str(user.id), "session_id": session_id}
        )

        # Перенаправляем на фронтенд с токеном в URL
        frontend_url = os.getenv("FRONTEND_URL", "https://localhost")
        return RedirectResponse(f"{frontend_url}/dashboard?token={access_token}")

    except Exception as e:
        raise HTTPException(400, f"OAuth authentication failed: {str(e)}")
