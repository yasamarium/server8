import pytest
from fastapi.testclient import TestClient
from src.server import app
from src.config import settings

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["model"] == "sd-turbo"

def test_root():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"

def test_image_generation_mock():
    res = client.post(
        "/v1/images/generations",
        headers={"Authorization": f"Bearer {settings.API_KEY}"},
        json={"prompt": "A modern cat", "size": "256x256"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert "b64_json" in data["data"][0]
