import secrets
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

# Методы, которые могут изменять состояние
UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Эндпоинты, которые НЕ требуют CSRF (webhooks, внешние API)
CSRF_EXEMPT_PATHS = {
    "/api/v1/agent/metrics",
    "/api/v1/agent/rules",
    "/api/v1/agent/health",
    "/api/v1/agent/simulate-attack",
    "/health",
    "/api/v1/health",
    "/api/v1/auth/login",       # Логин — до получения токена
    "/api/v1/auth/register",    # Регистрация — до получения токена
    "/api/v1/auth/oauth/google",
    "/api/v1/auth/oauth/github",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF-защита по схеме Double Submit Cookie.
    - При каждом ответе устанавливает cookie с CSRF-токеном (HttpOnly=False, чтобы JS мог прочитать).
    - Для небезопасных методов (POST/PUT/DELETE/PATCH) требует заголовок X-CSRF-Token,
      совпадающий со значением в cookie.
    """

    async def dispatch(self, request: Request, call_next):
        # Пропускаем exempt-эндпоинты
        if request.url.path in CSRF_EXEMPT_PATHS:
            response = await call_next(request)
            return response

        # Для небезопасных методов проверяем CSRF-токен
        if request.method in UNSAFE_METHODS:
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)

            # Если у пользователя есть токен авторизации — CSRF обязателен
            auth_header = request.headers.get("authorization")
            if auth_header and cookie_token:
                if not header_token or header_token != cookie_token:
                    raise HTTPException(
                        status_code=403,
                        detail="CSRF token missing or invalid"
                    )

        response = await call_next(request)

        # Устанавливаем CSRF-токен в cookie, если его ещё нет
        if not request.cookies.get(CSRF_COOKIE_NAME):
            new_token = secrets.token_urlsafe(32)
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=new_token,
                httponly=False,  # JS должен иметь доступ для чтения
                samesite="lax",
                secure=request.url.scheme == "https",
                max_age=3600 * 24,  # 24 часа
                path="/"
            )

        return response