import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, users, videos
from app.services.storage import ensure_bucket_exists


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Initializing RustFS storage")

    await ensure_bucket_exists()

    logger.info("RustFS storage initialized")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="YouTube clone backend",
    version="0.2.0",
    lifespan=lifespan,
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(videos.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "YouTube Copy API is running",
    }