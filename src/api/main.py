from __future__ import annotations

import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import router as records_router


MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", "1000000"))
API_TOKEN = os.getenv("API_TOKEN")

bearer_scheme = HTTPBearer(auto_error=False)


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")
        return await call_next(request)


def require_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if not API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_TOKEN is not configured on the server.",
        )

    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
        )


app = FastAPI(
    title="Canonical Reasoning Pipeline API",
    version="0.1.0",
    description="API for creating, validating, routing, and storing canonical reasoning records.",
)
app.add_middleware(ContentSizeLimitMiddleware)

app.include_router(records_router, dependencies=[Depends(require_api_token)])


@app.get("/")
def root():
    return {
        "message": "Canonical reasoning pipeline API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
