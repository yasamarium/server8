import pytest
from fastapi.testclient import TestClient
from src.server import app
from src.config import settings
from src.model import model_manager

def test_endpoints():
    model_manager.load_model()
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert res.json()["model"] == "sd-turbo"

        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "online"

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
