from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, users
from app.core.middleware import RequestIDMiddleware, limiter
from app.routers import upload

app = FastAPI(
    title="Net Protector API",
    description="Система активной защиты веб-ресурсов",
    version="0.4.0"
)

# 1. Request ID Middleware (UUIDv7)
app.add_middleware(RequestIDMiddleware)

# 2. CORS (SOP/CORS требования)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost", "http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# 3. Подключаем лимитер к приложению
app.state.limiter = limiter

# 4. Роутеры
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(upload.router)

# 5. Глобальный обработчик ошибок 413 и 415
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 413:
        return JSONResponse(
            status_code=413,
            content={
                "error": "payload_too_large",
                "detail": "Размер файла превышает лимит. Используйте chunked upload (/api/v1/upload/init)."
            }
        )
    if exc.status_code == 415:
        return JSONResponse(
            status_code=415,
            content={
                "error": "unsupported_media_type",
                "detail": "Неподдерживаемый тип файла (Content-Type)."
            }
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# 6. Health check эндпоинты
@app.get("/health")
def health_root():
    return {"status": "ok", "path": "/health"}

@app.get("/api/v1/health")
def health_api():
    return {"status": "ok", "path": "/api/v1/health"}