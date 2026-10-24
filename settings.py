import os
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

Color = Annotated[str, Field(pattern=r"\A#[0-9a-fA-F]{6}\z"), AfterValidator(str.upper)]


class RenderSettings(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    scale: Annotated[int, Field(ge=1, le=20)] = 4
    foreground: Color = "#FFFFFF"
    background: Color = "#000000"


class SettingsPatch(RenderSettings):
    pass


def apply_patch(current: RenderSettings, patch: SettingsPatch) -> RenderSettings:
    return RenderSettings.model_validate(
        current.model_dump() | patch.model_dump(exclude_unset=True)
    )


def load_timezone() -> ZoneInfo:
    name = os.environ.get("PIXEL_CLOCK_TIMEZONE", "Europe/Moscow")
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError(f"Invalid PIXEL_CLOCK_TIMEZONE: {name!r}") from error
