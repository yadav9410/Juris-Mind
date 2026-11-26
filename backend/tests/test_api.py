"""Basic tests for the first API increment."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_welcome_message():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "JurisMind API is running"


def test_liveness_endpoint_reports_running_api():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
