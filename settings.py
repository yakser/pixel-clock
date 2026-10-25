import os
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

HEX_COLOR_LENGTH = len("#RRGGBB")
MIN_SCALE = 1
MAX_SCALE = 20
DEFAULT_SCALE = 4
DEFAULT_FOREGROUND = "#FFFFFF"
DEFAULT_BACKGROUND = "#000000"
DEFAULT_TIMEZONE = "Europe/Moscow"
TIMEZONE_ENV_VAR = "PIXEL_CLOCK_TIMEZONE"

Color = Annotated[
    str,
    Field(pattern=r"^#[0-9a-fA-F]{6}$", min_length=HEX_COLOR_LENGTH, max_length=HEX_COLOR_LENGTH),
    AfterValidator(str.upper),
]


class RenderSettings(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    scale: Annotated[int, Field(ge=MIN_SCALE, le=MAX_SCALE)] = DEFAULT_SCALE
    foreground: Color = DEFAULT_FOREGROUND
    background: Color = DEFAULT_BACKGROUND


class SettingsPatch(RenderSettings):
    pass


def apply_patch(current: RenderSettings, patch: SettingsPatch) -> RenderSettings:
    return RenderSettings.model_validate(
        current.model_dump() | patch.model_dump(exclude_unset=True)
    )


def load_timezone() -> ZoneInfo:
    name = os.environ.get(TIMEZONE_ENV_VAR, DEFAULT_TIMEZONE)

    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError(f"Invalid {TIMEZONE_ENV_VAR}: {name!r}") from error
