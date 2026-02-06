# Presentation/API/main.py

import os
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Presentation.API.settings import settings
from Presentation.API.controllers.auth_controller import router as auth_router
from Presentation.API.controllers.ask_controller import router as ask_router
from Presentation.API.controllers.start_controller import router as start_router
from Presentation.API.workers.scheduler import start_scheduler


# -------------------------------------------------
# Workers Lifespan (startup / shutdown)
# -------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler do FastAPI.

    - Inicializa o APScheduler no startup
    - Finaliza o scheduler no shutdown
    """
    scheduler = None
    try:
        scheduler = start_scheduler()
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


# -------------------------------------------------
# App
# -------------------------------------------------

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# CORS a partir do settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Rotas com prefixo do settings
app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])
app.include_router(ask_router, prefix=f"{settings.API_PREFIX}/chat", tags=["Iracema"])
app.include_router(start_router, prefix=f"{settings.API_PREFIX}/start", tags=["Iracema"])


# -------------------------------------------------
# Local run (uvicorn)
# -------------------------------------------------

if __name__ == "__main__":
    env = os.getenv("ENVIRONMENT", "dev").lower()
    reload_flag = settings.API_RELOAD_ON_DEV and env != "docker"

    uvicorn.run(
        "Presentation.API.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=reload_flag,
    )
