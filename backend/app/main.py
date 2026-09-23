import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from app.database import init_db
from prometheus_fastapi_instrumentator import Instrumentator 

init_db()

# === ИМПОРТЫ РОУТЕРОВ ===
from app.api import auth, users, metrics, admin, dashboard, upload, two_factor

# === ИМПОРТЫ MIDDLEWARE ===
from app.core.middleware import RequestIDMiddleware, limiter
from app.core.csrf import CSRFMiddleware  # <-- ДОБАВЛЕНО

app = FastAPI(
    title="Net Protector API",
    description="Система активной защиты веб-ресурсов",
    version="0.5.0"
)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    tags=["prometheus"]
)

# === 1. SessionMiddleware ===
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-32-chars")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# === 2. CSRF Middleware (Double Submit Cookie) ===
app.add_middleware(CSRFMiddleware)  # <-- ДОБАВЛЕНО

# === 3. Request ID Middleware (UUIDv7) ===
app.add_middleware(RequestIDMiddleware)

# === 4. CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost", "http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
)

# === 5. Rate limiter ===
app.state.limiter = limiter

# === 6. Подключение роутеров ===
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(metrics.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(two_factor.router)

# === 7. Глобальный обработчик ошибок ===
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 413:
        return JSONResponse(
            status_code=413,
            content={
                "error": "payload_too_large",
                "detail": "Размер файла превышает лимит."
            }
        )
    if exc.status_code == 415:
        return JSONResponse(
            status_code=415,
            content={
                "error": "unsupported_media_type",
                "detail": "Неподдерживаемый тип файла."
            }
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# === 8. Health check ===
@app.get("/health")
def health_root():
    return {"status": "ok", "path": "/health"}

@app.get("/api/v1/health")
def health_api():
    return {"status": "ok", "path": "/api/v1/health"}