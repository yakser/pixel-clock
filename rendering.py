from io import BytesIO

from PIL import Image, ImageColor

from settings import RenderSettings

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


def render_time_png(time_text: str, settings: RenderSettings) -> bytes:
    image = Image.new("RGB", (29, 7), settings.background)
    foreground = ImageColor.getrgb(settings.foreground)
    offset = 1
    for character in time_text:
        glyph = GLYPHS[character]
        for y, row in enumerate(glyph, start=1):
            for x, pixel in enumerate(row, start=offset):
                if pixel == "1":
                    image.putpixel((x, y), foreground)
        offset += len(glyph[0]) + 1
    image = image.resize((29 * settings.scale, 7 * settings.scale), Image.Resampling.NEAREST)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
