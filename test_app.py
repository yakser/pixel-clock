import logging
import tomllib
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app_final import create_app, get_now


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
