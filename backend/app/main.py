from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, users, upload, admin, agent
from app.core.middleware import RequestIDMiddleware, limiter

app = FastAPI(
    title="Net Protector API",
    description="System for active protection of web resources",
    version="1.0.0"
)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost", "http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.state.limiter = limiter

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(admin.router)
app.include_router(agent.router)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 413:
        return JSONResponse(
            status_code=413,
            content={"error": "payload_too_large", "detail": "File size exceeds limit. Use chunked upload."}
        )
    if exc.status_code == 415:
        return JSONResponse(
            status_code=415,
            content={"error": "unsupported_media_type", "detail": "Unsupported file type."}
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/health")
def health_root():
    return {"status": "ok", "path": "/health"}

@app.get("/api/v1/health")
def health_api():
    return {"status": "ok", "path": "/api/v1/health"}