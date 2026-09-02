from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
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


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/hour")  # Rate limit на регистрацию
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter((User.email == data.email) | (User.username == data.username)).first():
        raise HTTPException(400, "Email или username уже заняты")

    user = User(email=data.email, username=data.username, password_hash=hash_password(data.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit на логин (защита от brute-force)
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверные учетные данные")
    if not user.is_active:
        raise HTTPException(403, "Аккаунт заблокирован")

    # Проверка 2FA
    if user.is_2fa_enabled:
        if not data.totp_code or not pyotp.TOTP(user.totp_secret).verify(data.totp_code):
            raise HTTPException(401, "Неверный код 2FA")

    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id, user_id=user.id, ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"), expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(session)
    db.commit()

    return {"access_token": create_access_token({"sub": str(user.id), "session_id": session_id}),
            "token_type": "bearer"}


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

