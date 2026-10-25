import asyncio
import logging
import re
import tomllib
from datetime import datetime
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app_final import create_app, get_now
from rendering import render_time_png
from settings import RenderSettings

BLACK_RGB = (0, 0, 0)
WHITE_RGB = (255, 255, 255)
GREEN_RGB = (0, 255, 0)


def test_health():
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_version():
    with TestClient(create_app()) as client:
        response = client.get("/version")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"version": "0.1.0"}

    metadata = tomllib.loads(Path(__file__).with_name("pyproject.toml").read_text())

    assert response.json()["version"] == metadata["project"]["version"]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv("PIXEL_CLOCK_TIMEZONE", raising=False)


@pytest.fixture
def fixed_app():
    application = create_app()
    application.dependency_overrides[get_now] = lambda: datetime.fromisoformat(
        "2026-01-01T22:04:05+00:00"
    )

    return application


def test_time_default(fixed_app):
    with TestClient(fixed_app) as client:
        response = client.get("/time")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"time": "01:04:05", "timezone": "Europe/Moscow"}
    assert response.headers["cache-control"] == "no-store"


def test_time_timezone(monkeypatch, fixed_app):
    monkeypatch.setenv("PIXEL_CLOCK_TIMEZONE", "UTC")

    with TestClient(fixed_app) as client:
        assert client.get("/time").json() == {"time": "22:04:05", "timezone": "UTC"}


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        ("2026-03-29T00:59:59+00:00", "01:59:59"),
        ("2026-03-29T01:00:00+00:00", "03:00:00"),
    ],
)
def test_time_dst(monkeypatch, fixed_app, instant, expected):
    monkeypatch.setenv("PIXEL_CLOCK_TIMEZONE", "Europe/Berlin")
    fixed_app.dependency_overrides[get_now] = lambda: datetime.fromisoformat(instant)

    with TestClient(fixed_app) as client:
        assert client.get("/time").json() == {"time": expected, "timezone": "Europe/Berlin"}


@pytest.mark.parametrize("zone", ["", "Not/AZone", "/etc/passwd", "../UTC"])
def test_invalid_timezone(monkeypatch, zone):
    monkeypatch.setenv("PIXEL_CLOCK_TIMEZONE", zone)

    with pytest.raises(ValueError, match="PIXEL_CLOCK_TIMEZONE"), TestClient(create_app()):
        pass


def test_startup_log(caplog):
    with caplog.at_level(logging.INFO), TestClient(create_app()):
        pass

    assert "Europe/Moscow" in caplog.text


def test_time_single_clock_read(fixed_app):
    calls = []

    def clock():
        calls.append(1)

        return datetime.fromisoformat("2026-01-01T22:04:05+00:00")

    fixed_app.dependency_overrides[get_now] = clock

    with TestClient(fixed_app) as client:
        assert client.get("/time").status_code == HTTPStatus.OK

    assert len(calls) == 1


def test_png_default(fixed_app):
    with TestClient(fixed_app) as client:
        response = client.get("/time-png")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"

    image = Image.open(BytesIO(response.content))

    assert image.format == "PNG"
    assert image.mode == "RGB"
    assert image.size == (116, 28)
    assert image.getpixel((0, 0)) == BLACK_RGB
    assert set(image.get_flattened_data()) == {BLACK_RGB, WHITE_RGB}


@pytest.mark.parametrize(("scale", "size"), [(1, (29, 7)), (4, (116, 28)), (20, (580, 140))])
def test_png_scaling(scale, size):
    image = Image.open(BytesIO(render_time_png("00:00:00", RenderSettings(scale=scale))))

    assert image.size == size

    expected_rows = ["111", "101", "101", "101", "111"]
    digit_padding = 1

    for y, row in enumerate(expected_rows, start=digit_padding):
        for x, value in enumerate(row, start=digit_padding):
            for dy in range(scale):
                for dx in range(scale):
                    assert image.getpixel((x * scale + dx, y * scale + dy)) == (
                        WHITE_RGB if value == "1" else BLACK_RGB
                    )

    for x in range(size[0]):
        assert image.getpixel((x, 0)) == BLACK_RGB
        assert image.getpixel((x, size[1] - 1)) == BLACK_RGB

    first_digit_gap = 4 * scale
    second_digit_gap = 8 * scale
    border_and_gap_columns = (0, first_digit_gap, second_digit_gap, size[0] - 1)

    for y in range(size[1]):
        for x in border_and_gap_columns:
            assert image.getpixel((x, y)) == BLACK_RGB


@pytest.mark.parametrize(
    ("digit", "rows"),
    [
        ("0", ["111", "101", "101", "101", "111"]),
        ("1", ["010", "110", "010", "010", "111"]),
        ("2", ["111", "001", "111", "100", "111"]),
        ("3", ["111", "001", "111", "001", "111"]),
        ("4", ["101", "101", "111", "001", "001"]),
        ("5", ["111", "100", "111", "001", "111"]),
        ("6", ["111", "100", "111", "101", "111"]),
        ("7", ["111", "001", "010", "010", "010"]),
        ("8", ["111", "101", "111", "101", "111"]),
        ("9", ["111", "101", "111", "001", "111"]),
    ],
)
def test_png_glyphs(digit, rows):
    image = Image.open(BytesIO(render_time_png(f"00:00:0{digit}", RenderSettings(scale=1))))
    top_padding = 1
    glyph_height = 5
    last_digit_column = 25
    colon_columns = (9, 19)

    for y, row in enumerate(rows, start=top_padding):
        for x, value in enumerate(row, start=last_digit_column):
            assert image.getpixel((x, y)) == (WHITE_RGB if value == "1" else BLACK_RGB)

    glyph_rows = range(top_padding, top_padding + glyph_height)

    for x in colon_columns:
        assert [image.getpixel((x, y)) for y in glyph_rows] == [
            BLACK_RGB,
            WHITE_RGB,
            BLACK_RGB,
            WHITE_RGB,
            BLACK_RGB,
        ]


def test_png_single_clock_read(fixed_app):
    calls = []

    def clock():
        calls.append(1)

        return datetime.fromisoformat("2026-01-01T09:34:56+00:00")

    fixed_app.dependency_overrides[get_now] = clock

    with TestClient(fixed_app) as client:
        response = client.get("/time-png")

    assert response.status_code == HTTPStatus.OK
    assert len(calls) == 1
    assert response.content == render_time_png("12:34:56", RenderSettings())


def test_settings_partial(fixed_app):
    with TestClient(fixed_app) as client:
        response = client.patch("/settings", json={"foreground": "#00ff00", "scale": 6})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"scale": 6, "foreground": "#00FF00", "background": "#000000"}

        image = Image.open(BytesIO(client.get("/time-png").content))

        assert image.size == (174, 42)
        assert set(image.get_flattened_data()) == {GREEN_RGB, BLACK_RGB}
        assert client.patch("/settings", json={"background": "#ff00ff"}).json() == {
            "scale": 6,
            "foreground": "#00FF00",
            "background": "#FF00FF",
        }


@pytest.mark.parametrize(("scale", "expected_size"), [(1, (29, 7)), (20, (580, 140))])
def test_settings_boundaries(fixed_app, scale, expected_size):
    with TestClient(fixed_app) as client:
        response = client.patch("/settings", json={"scale": scale})

        assert response.status_code == HTTPStatus.OK
        assert response.json()["scale"] == scale

        image = Image.open(BytesIO(client.get("/time-png").content))

        assert image.size == expected_size


@pytest.mark.parametrize(
    "payload",
    [
        *({"scale": scale} for scale in [0, 21, 1.5, 4.0, "4", True, None]),
        *(
            {field: color}
            for field in ["foreground", "background"]
            for color in ["red", "#FFF", "#GG0000", "#FFFFFF\n", 123, None]
        ),
        {"unknown": 1},
        [],
        {"scale": 6, "foreground": "bad"},
    ],
)
def test_settings_invalid(fixed_app, payload):
    with TestClient(fixed_app) as client:
        initial = client.patch("/settings", json={})

        assert initial.status_code == HTTPStatus.OK

        response = client.patch("/settings", json=payload)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert client.patch("/settings", json={}).json() == initial.json()


@pytest.mark.parametrize("body", ["", "{", "null", '"hello"'])
def test_settings_invalid_body(fixed_app, body):
    with TestClient(fixed_app) as client:
        response = client.patch(
            "/settings", content=body, headers={"Content-Type": "application/json"}
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert client.patch("/settings", json={}).json() == {
            "scale": 4,
            "foreground": "#FFFFFF",
            "background": "#000000",
        }


def test_settings_noop(fixed_app):
    with TestClient(fixed_app) as client:
        response = client.patch("/settings", json={})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"scale": 4, "foreground": "#FFFFFF", "background": "#000000"}
        assert client.patch("/settings", json={}).json() == response.json()


def test_settings_same_colors(fixed_app):
    with TestClient(fixed_app) as client:
        assert (
            client.patch("/settings", json={"foreground": "#000000"}).status_code == HTTPStatus.OK
        )

        image = Image.open(BytesIO(client.get("/time-png").content))

        assert set(image.get_flattened_data()) == {BLACK_RGB}


def test_settings_isolated(fixed_app):
    with TestClient(fixed_app) as first, TestClient(create_app()) as second:
        assert first.patch("/settings", json={"scale": 9}).status_code == HTTPStatus.OK
        assert first.patch("/settings", json={}).json()["scale"] == 9
        assert second.patch("/settings", json={}).json()["scale"] == 4

    with TestClient(create_app()) as restarted:
        assert restarted.patch("/settings", json={}).json()["scale"] == 4


def test_settings_concurrent(fixed_app):
    async def exercise():
        async with fixed_app.router.lifespan_context(fixed_app):
            transport = httpx.ASGITransport(app=fixed_app)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                responses = await asyncio.gather(
                    client.patch("/settings", json={"scale": 7}),
                    client.patch("/settings", json={"foreground": "#123456"}),
                )

                assert all(response.status_code == HTTPStatus.OK for response in responses)

                response = await client.patch("/settings", json={})

                assert response.json() == {
                    "scale": 7,
                    "foreground": "#123456",
                    "background": "#000000",
                }

    asyncio.run(exercise())


def test_settings_log(fixed_app, caplog):
    with caplog.at_level(logging.INFO), TestClient(fixed_app) as client:
        assert client.patch("/settings", json={"scale": 8}).status_code == HTTPStatus.OK

        caplog.clear()
        response = client.patch("/settings", json={"foreground": "#00ff00"})

    assert response.status_code == HTTPStatus.OK

    messages = [
        record.getMessage()
        for record in caplog.records
        if "Rendering settings updated" in record.getMessage()
    ]

    assert len(messages) == 1
    assert (
        "old_settings={'scale': 8, 'foreground': '#FFFFFF', 'background': '#000000'}" in messages[0]
    )
    assert (
        "new_settings={'scale': 8, 'foreground': '#00FF00', 'background': '#000000'}" in messages[0]
    )


def test_settings_invalid_does_not_log_update(fixed_app, caplog):
    with caplog.at_level(logging.INFO), TestClient(fixed_app) as client:
        response = client.patch("/settings", json={"scale": 100})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "Rendering settings updated" not in caplog.text


def test_png_log(fixed_app, caplog):
    with caplog.at_level(logging.INFO), TestClient(fixed_app) as client:
        assert (
            client.patch("/settings", json={"scale": 6, "foreground": "#00ff00"}).status_code
            == HTTPStatus.OK
        )

        caplog.clear()
        response = client.get("/time-png")

    assert response.status_code == HTTPStatus.OK

    image = Image.open(BytesIO(response.content))
    messages = [
        record.getMessage() for record in caplog.records if "PNG generated" in record.getMessage()
    ]

    assert len(messages) == 1

    message = messages[0]

    assert "settings={'scale': 6, 'foreground': '#00FF00', 'background': '#000000'}" in message
    assert "time=01:04:05" in message
    assert "timezone=Europe/Moscow" in message
    assert f"width={image.width} height={image.height}" in message
    assert "format=PNG mode=RGB" in message
    assert f"bytes={len(response.content)}" in message


def test_color_schema_is_portable(fixed_app):
    with TestClient(fixed_app) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    for model in ["RenderSettings", "SettingsPatch"]:
        for field in ["foreground", "background"]:
            color = schemas[model]["properties"][field]

            assert r"\A" not in color["pattern"]
            assert r"\z" not in color["pattern"]
            assert color["minLength"] == color["maxLength"] == 7

            for value, valid in [
                ("#FFFFFF", True),
                ("#00ff00", True),
                ("red", False),
                ("#FFF", False),
                ("#FFFFFF\n", False),
                ("A#FFFFFFz", False),
            ]:
                schema_accepts = len(value) == 7 and re.search(color["pattern"], value) is not None

                assert schema_accepts == valid
