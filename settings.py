import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict


def load_timezone() -> ZoneInfo:
    name = os.environ.get("PIXEL_CLOCK_TIMEZONE", "Europe/Moscow")
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError(f"Invalid PIXEL_CLOCK_TIMEZONE: {name!r}") from error



class RenderSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    scale: int = 4
    foreground: str = "#FFFFFF"
    background: str = "#000000"
