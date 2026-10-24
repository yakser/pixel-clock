import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def load_timezone() -> ZoneInfo:
    name = os.environ.get("PIXEL_CLOCK_TIMEZONE", "Europe/Moscow")
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError(f"Invalid PIXEL_CLOCK_TIMEZONE: {name!r}") from error
