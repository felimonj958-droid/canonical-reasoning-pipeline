from __future__ import annotations

from fastapi import FastAPI

from src.api.routes import router as ingest_router


app = FastAPI(title="LSAT Multimodal Pipeline API", version="0.1.0")
app.include_router(ingest_router)


@app.get("/")
def root():
    return {
        "message": "LSAT pipeline API is running",
        "docs": "/docs",
    }
