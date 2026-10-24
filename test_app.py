import logging
import tomllib
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app_final import create_app, get_now
from rendering import render_time_png
from settings import RenderSettings


def test_health():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version():
    with TestClient(create_app()) as client:
        response = client.get("/version")
    assert response.status_code == 200
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
    assert response.status_code == 200
    assert response.json() == {"time": "01:04:05", "timezone": "Europe/Moscow"}
    assert response.headers["cache-control"] == "no-store"


def test_time_timezone(monkeypatch, fixed_app):
    monkeypatch.setenv("PIXEL_CLOCK_TIMEZONE", "UTC")
    with TestClient(fixed_app) as client:
        assert client.get("/time").json() == {"time": "22:04:05", "timezone": "UTC"}


@pytest.mark.parametrize(
    "instant,expected",
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
    with pytest.raises(ValueError, match="PIXEL_CLOCK_TIMEZONE"):
        with TestClient(create_app()):
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
        assert client.get("/time").status_code == 200
    assert len(calls) == 1


def test_png_default(fixed_app):
    with TestClient(fixed_app) as client:
        response = client.get("/time-png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    image = Image.open(BytesIO(response.content))
    assert image.format == "PNG"
    assert image.mode == "RGB"
    assert image.size == (116, 28)
    assert image.getpixel((0, 0)) == (0, 0, 0)
    assert set(image.get_flattened_data()) == {(0, 0, 0), (255, 255, 255)}


@pytest.mark.parametrize("scale,size", [(1, (29, 7)), (4, (116, 28)), (20, (580, 140))])
def test_png_scaling(scale, size):
    image = Image.open(BytesIO(render_time_png("00:00:00", RenderSettings(scale=scale))))
    assert image.size == size
    expected_rows = ["111", "101", "101", "101", "111"]
    for y, row in enumerate(expected_rows, start=1):
        for x, value in enumerate(row, start=1):
            for dy in range(scale):
                for dx in range(scale):
                    assert image.getpixel((x * scale + dx, y * scale + dy)) == (
                        (255, 255, 255) if value == "1" else (0, 0, 0)
                    )
    for x in range(size[0]):
        assert image.getpixel((x, 0)) == (0, 0, 0)
        assert image.getpixel((x, size[1] - 1)) == (0, 0, 0)
    for y in range(size[1]):
        for x in [0, 4 * scale, 8 * scale, size[0] - 1]:
            assert image.getpixel((x, y)) == (0, 0, 0)


@pytest.mark.parametrize(
    "digit,rows",
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
    for y, row in enumerate(rows, start=1):
        for x, value in enumerate(row, start=25):
            assert image.getpixel((x, y)) == ((255, 255, 255) if value == "1" else (0, 0, 0))
    for x in [9, 19]:
        assert [image.getpixel((x, y)) for y in range(1, 6)] == [
            (0, 0, 0),
            (255, 255, 255),
            (0, 0, 0),
            (255, 255, 255),
            (0, 0, 0),
        ]


def test_png_single_clock_read(fixed_app):
    calls = []

    def clock():
        calls.append(1)
        return datetime.fromisoformat("2026-01-01T09:34:56+00:00")

    fixed_app.dependency_overrides[get_now] = clock
    with TestClient(fixed_app) as client:
        response = client.get("/time-png")
    assert response.status_code == 200
    assert len(calls) == 1
    assert response.content == render_time_png("12:34:56", RenderSettings())
