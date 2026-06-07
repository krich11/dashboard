from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.routers import devices, health, reachability, status
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
    app.include_router(settings_router.router)
    return app


app = create_app()