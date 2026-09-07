from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import User, Session as SessionModel
from app.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from datetime import datetime, timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Session as SessionModel
from app.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.middleware import limiter
import pyotp, qrcode, io, base64, uuid, os
from datetime import datetime, timedelta
from authlib.integrations.starlette_client import OAuth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Настройка OAuth (пример для Google и GitHub)
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
oauth.register(
    name="github",
    client_id=os.getenv("GITHUB_CLIENT_ID", ""),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

# === Мастер-ключ для регистрации админов ===
MASTER_INVITE_KEY = os.getenv("MASTER_INVITE_KEY", "NP-MASTER-2026-SUPER-ADMIN")
MASTER_INVITE_MAX_USES = int(os.getenv("MASTER_INVITE_MAX_USES", "-1"))

# Счётчик использований мастер-ключа (в памяти; в продакшене хранить в БД)
_master_key_uses = 0


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/hour")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.

    Логика ключей:
    - Если invitation_key == MASTER_INVITE_KEY → пользователь получает роль 'admin'
    - Иначе ключ ищется в таблице invitation_keys → роль 'user'
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
                f"Мастер-ключ достиг лимита использований ({MASTER_INVITE_MAX_USES})"
            )
        role = "admin"
        is_master_key = True
    else:
        # Обычный одноразовый ключ из БД
        invite = db.query(InvitationKey).filter(
            InvitationKey.key == data.invitation_key,
            InvitationKey.is_used == False
        ).first()

        if not invite:
            raise HTTPException(
                403,
                "Недействительный или уже использованный ключ регистрации. "
                "Получите ключ у администратора."
            )

    # 2. Проверка уникальности email и username
    if db.query(User).filter(
            or_(User.email == data.email, User.username == data.username)
    ).first():
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


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверные учетные данные")
    if not user.is_active:
        raise HTTPException(403, "Аккаунт заблокирован")

    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(session)
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "session_id": session_id})
    return {"access_token": access_token, "token_type": "bearer"}


# === 2FA Эндпоинты ===
@router.post("/2fa/setup")
def setup_2fa(user: User = Depends(lambda: None),
              db: Session = Depends(get_db)):  # Заглушка для Depends(get_current_user), см. ниже
    # В реальном коде здесь будет: user: User = Depends(get_current_user)
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()

    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Net Protector")
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return {"secret": secret, "qr_code": f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"}


@router.post("/2fa/verify")
def verify_2fa(code: str, user: User = Depends(lambda: None), db: Session = Depends(get_db)):
    if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(code):
        raise HTTPException(400, "Неверный код 2FA")
    user.is_2fa_enabled = True
    db.commit()
    return {"message": "2FA успешно включен"}


# === OAuth Эндпоинты ===
@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    if provider not in ["google", "github"]:
        raise HTTPException(400, "Неподдерживаемый провайдер")
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    return await getattr(oauth, provider).authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback", name="oauth_callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    token = await getattr(oauth, provider).authorize_access_token(request)
    raise HTTPException(501, "OAuth callback в разработке (требует настройки переменных окружения)")

