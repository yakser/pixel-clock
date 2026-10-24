import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app_final import create_app


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
