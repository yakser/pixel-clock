import logging
import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response

from settings import load_timezone

logger = logging.getLogger("uvicorn.error")


def get_now() -> datetime:
    return datetime.now(UTC)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.timezone = load_timezone()
    logger.info("Pixel Clock started, timezone=%s", application.state.timezone.key)
    yield


def create_app() -> FastAPI:
    metadata = tomllib.loads(Path(__file__).with_name("pyproject.toml").read_text())
    version = metadata["project"]["version"]
    application = FastAPI(title="Pixel Clock", version=version, lifespan=lifespan)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/version")
    async def get_version() -> dict[str, str]:
        return {"version": version}

    @application.get("/time")
    async def get_time(
        request: Request, response: Response, now: Annotated[datetime, Depends(get_now)]
    ) -> dict[str, str]:
        timezone = request.app.state.timezone
        response.headers["Cache-Control"] = "no-store"
        return {"time": now.astimezone(timezone).strftime("%H:%M:%S"), "timezone": timezone.key}

    return application


app = create_app()
