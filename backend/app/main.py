from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR, get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.routers import dashboards, devices, health, reachability, status, widgets
from app.routers import settings as settings_router
from app.services.collector_service import collector_service
from app.services.seed import seed_from_mocks


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_from_mocks(db)
    finally:
        db.close()
    if not settings.testing:
        collector_service.start()
    yield
    if not settings.testing:
        collector_service.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(status.router)
    app.include_router(reachability.router)
    app.include_router(devices.router)
    app.include_router(dashboards.router)
    app.include_router(settings_router.router)
    app.include_router(widgets.router)

    static_dir = settings.frontend_static_dir
    if static_dir is None:
        default_dist = ROOT_DIR / "frontend" / "dist"
        if default_dist.is_dir():
            static_dir = str(default_dist)
    if static_dir and Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()