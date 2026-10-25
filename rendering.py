from io import BytesIO

from PIL import Image, ImageColor

from settings import RenderSettings

IMAGE_PADDING = 1
GLYPH_GAP = 1
TIME_LAYOUT = "00:00:00"

GLYPHS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    ":": ("0", "1", "0", "1", "0"),
}

BASE_IMAGE_WIDTH = (
    sum(len(GLYPHS[character][0]) for character in TIME_LAYOUT)
    + GLYPH_GAP * (len(TIME_LAYOUT) - 1)
    + IMAGE_PADDING * 2
)
BASE_IMAGE_HEIGHT = len(GLYPHS["0"]) + IMAGE_PADDING * 2


def image_size(scale: int) -> tuple[int, int]:
    return BASE_IMAGE_WIDTH * scale, BASE_IMAGE_HEIGHT * scale


def render_time_png(time_text: str, settings: RenderSettings) -> bytes:
    image = Image.new("RGB", (BASE_IMAGE_WIDTH, BASE_IMAGE_HEIGHT), settings.background)
    foreground = ImageColor.getrgb(settings.foreground)
    offset = IMAGE_PADDING

    for character in time_text:
        glyph = GLYPHS[character]

        for y, row in enumerate(glyph, start=IMAGE_PADDING):
            for x, pixel in enumerate(row, start=offset):
                if pixel == "1":
                    image.putpixel((x, y), foreground)

        offset += len(glyph[0]) + GLYPH_GAP

    image = image.resize(image_size(settings.scale), Image.Resampling.NEAREST)

    output = BytesIO()
    image.save(output, format="PNG")

    return output.getvalue()
