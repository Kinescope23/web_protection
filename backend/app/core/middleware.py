from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.utils.uuid7 import get_uuid7  # <-- Импортируем get_uuid7
import logging
import time

logger = logging.getLogger("net_protector")
logging.basicConfig(level=logging.INFO,
                    format='{"time":"%(asctime)s", "request_id":"%(request_id)s", "method":"%(method)s", "path":"%(path)s", "status":%(status)s}')

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Явно вызываем нашу функцию get_uuid7(), если заголовок не передан
        request_id = request.headers.get("X-Request-ID") or get_uuid7()
        request.state.request_id = request_id

        start_time = time.time()
        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Request completed", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms
        })
        return response