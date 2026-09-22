import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router
from app.config import get_settings
from app.db import engine, init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Corporate Avatar Service",
    description="Генерация корпоративных аватаров сотрудников (интеграция с 1С:УНФ)",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health", tags=["service"])
def health():
    """Без авторизации — для docker healthcheck и мониторинга."""
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok", "backend": get_settings().pipeline_backend}
