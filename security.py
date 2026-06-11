# security.py
import os
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

SECRET_KEYS = {
    os.getenv("VITE_LOCAL_API_KEY", "dev-secret-123"): "admin",
}

class LimitUploadSize(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 1_000_000:
                raise HTTPException(status_code=413, detail="Payload too large")
        return await call_next(request)

async def get_current_role(api_key: str = Security(api_key_header)):
    if api_key in SECRET_KEYS:
        return SECRET_KEYS[api_key]
    raise HTTPException(status_code=403, detail="Invalid or Missing API Key")
