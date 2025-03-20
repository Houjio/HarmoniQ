import pytest
from fastapi.testclient import TestClient

from harmoniq.webserver import app

client = TestClient(app)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "HarmoniQ" in response.text


def test_ping():
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}
