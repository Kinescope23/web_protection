import secrets
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

CSRF_EXEMPT_PATHS = {
    "/api/v1/agent/metrics",
    "/api/v1/agent/rules",
    "/api/v1/agent/health",
    "/api/v1/agent/simulate-attack",
    "/health",
    "/api/v1/health",
    "/api/v1/auth/login",       
    "/api/v1/auth/register",    
    "/api/v1/auth/oauth/google",
    "/api/v1/auth/oauth/github",
}

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        
        if request.url.path in CSRF_EXEMPT_PATHS:
            response = await call_next(request)
            return response

        if request.method in UNSAFE_METHODS:
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            auth_header = request.headers.get("authorization")

            if auth_header:
                if not cookie_token or not header_token or header_token != cookie_token:
                    raise HTTPException(
                        status_code=403,
                        detail="CSRF token missing or invalid"
                    )

        response = await call_next(request)

        
        if not request.cookies.get(CSRF_COOKIE_NAME):
            new_token = secrets.token_urlsafe(32)
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=new_token,
                httponly=False,
                samesite="lax",
                secure=request.url.scheme == "https",
                max_age=3600 * 24,
                path="/"
            )

        return response