from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analytics,
    auth,
    dev,
    events,
    experiments,
    finance,
    forecast,
    health,
    imports,
    mock,
    recommendations,
)
from app.config import get_settings
from app.db import SessionLocal
from app.services.categories import ensure_system_categories


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as db:
        ensure_system_categories(db)
    yield


def create_app(*, seed_on_startup: bool = True) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="MoneyForecast AI API",
        version="0.1.0",
        description="Учёт расходов, ИИ-прогноз трат и предупреждение о кассовых разрывах.",
        lifespan=lifespan if seed_on_startup else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        health.router,
        auth.router,
        finance.router,
        imports.router,
        analytics.router,
        forecast.router,
        recommendations.router,
        experiments.router,
        mock.router,
        events.router,
        dev.router,
    ):
        app.include_router(router)
    return app


app = create_app()
