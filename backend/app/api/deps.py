from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt

from app.database import get_db
from app.models import User
from app.core.security import SECRET_KEY, ALGORITHM

# auto_error=False: без заголовка Authorization HTTPBearer по умолчанию отдаёт 403 Forbidden.
# Мы пробрасываем вместо этого корректный 401 Unauthorized, чтобы фронтенд мог штатно
# перенаправить пользователя на страницу логина (согласно требованиям лабы).
security = HTTPBearer(auto_error=False)


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db),
) -> User:
    # 1. Проверка наличия заголовка Authorization
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Валидация JWT-токена
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Невалидный токен")
    except Exception:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    # 3. Проверка существования и активности пользователя в БД
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401, detail="Пользователь не найден или заблокирован"
        )

    return user