import logging
import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response

from rendering import render_time_png
from settings import RenderSettings, SettingsPatch, apply_patch, load_timezone

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

    application.state.render_settings = RenderSettings()

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

    @application.get(
        "/time-png", response_class=Response, responses={200: {"content": {"image/png": {}}}}
    )
    async def get_time_png(
        request: Request, now: Annotated[datetime, Depends(get_now)]
    ) -> Response:
        time_text = now.astimezone(request.app.state.timezone).strftime("%H:%M:%S")
        snapshot = request.app.state.render_settings
        return Response(
            render_time_png(time_text, snapshot),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    @application.patch("/settings")
    async def update_settings(request: Request, patch: SettingsPatch) -> RenderSettings:
        snapshot = apply_patch(request.app.state.render_settings, patch)
        request.app.state.render_settings = snapshot
        logger.info("Rendering settings updated: %s", snapshot.model_dump())
        return snapshot

    return application


app = create_app()
