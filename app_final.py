import tomllib
from pathlib import Path

from fastapi import FastAPI


def create_app() -> FastAPI:
    metadata = tomllib.loads(Path(__file__).with_name("pyproject.toml").read_text())
    version = metadata["project"]["version"]
    application = FastAPI(title="Pixel Clock", version=version)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/version")
    async def get_version() -> dict[str, str]:
        return {"version": version}

    return application


app = create_app()
