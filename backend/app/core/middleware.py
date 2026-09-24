from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.utils.uuid7 import get_uuid7
import logging
import time
import json

# ИСПРАВЛЕНО: Убираем жесткий format, который требовал request_id во ВСЕХ логах.
# Теперь обычный logger.info("текст") будет работать без ошибок.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("net_protector")

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or get_uuid7()
        request.state.request_id = request_id

        start_time = time.time()
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Логируем HTTP-запросы как JSON-строку (для соответствия требованиям)
        log_data = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        logger.info(json.dumps(log_data))

        return response
