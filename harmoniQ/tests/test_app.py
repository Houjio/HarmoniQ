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


def test_create_station():
    station_data = {
        "nom": "Test Station",
        "IATA_ID": "TS123",
        "MSC_ID": "MSC123",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "elevation_m": 10,
    }
    response = client.post("/api/stations", json=station_data)
    assert response.status_code == 200
    assert response.json()["nom"] == "Test Station"
    assert response.json()["IATA_ID"] == "TS123"


def test_get_all_stations():
    response = client.get("/api/stations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_station_by_id():
    station_id = 1  # Assuming a station with ID 1 exists
    response = client.get(f"/api/stations/{station_id}")
    assert response.status_code == 200
    assert "nom" in response.json()


def test_get_station_by_iata_id():
    iata_id = "TS123"  # Assuming a station with IATA ID TS123 exists
    response = client.get(f"/api/stations/iata/{iata_id}")
    assert response.status_code == 200
    assert response.json()["IATA_ID"] == "TS123"


def test_delete_station():
    iata_id = "TS123"  # Assuming a station with IATA ID TS123 exists
    station_id = client.get(f"/api/stations/iata/{iata_id}").json()["id"]
    response = client.delete(f"/api/stations/{station_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Station supprimée"}


def test_n_nearest():
    latitude = 45.514274
    longitude = -73.5730908  # Downtown Montreal
    n = 3

    response = client.post(
        f"/api/stations/n_proches?latitude={latitude}&longitude={longitude}&n={n}"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == n

    first_name = "MCTAVISH"
    assert response.json()[0]["nom"] == first_name

    second_name = "Montreal/St-Hubert"
    assert response.json()[1]["nom"] == second_name
