import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, create_db_tables
from app.seed_data import seed_database
from app.traffic_service import traffic_service

client = TestClient(app)

def setup_module():
    create_db_tables()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

def test_system_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "database" in data
    assert data["traffic_active_bottlenecks"] > 0

def test_locations_list():
    response = client.get("/api/locations")
    assert response.status_code == 200
    locations = response.json()
    assert len(locations) >= 14
    names = [loc["name"] for loc in locations]
    assert "Majestic" in names
    assert "MG Road" in names
    assert "Indiranagar" in names
    assert "Whitefield" in names
    assert "Victoria Hospital" in names
    assert "Upparpet Police Station" in names

def test_shortest_distance_route():
    payload = {
        "origin": "Majestic",
        "destination": "Indiranagar",
        "criteria": "distance"
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["origin"] == "Majestic"
    assert data["destination"] == "Indiranagar"
    assert len(data["path"]) >= 2
    assert data["total_distance_km"] > 0

def test_fastest_time_route_with_traffic():
    payload = {
        "origin": "Majestic",
        "destination": "Whitefield",
        "criteria": "time"
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert "Whitefield" in data["path"]
    assert len(data["directions"]) > 0

def test_unreachable_route_handling():
    payload = {
        "origin": "Majestic",
        "destination": "Nelamangala Isolated Depot",
        "criteria": "time"
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert "No route found" in data["message"] or "disconnected" in data["message"]

def test_sos_emergency_hospital():
    payload = {
        "current_location": "Indiranagar",
        "service_type": "hospital"
    }
    response = client.post("/api/sos", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["is_emergency"] is True
    assert data["emergency_type"] == "hospital"
    # From Indiranagar, Manipal Hospital is adjacent (HAL Old Airport Road)
    assert data["destination"] == "Manipal Hospital"

def test_sos_emergency_police():
    payload = {
        "current_location": "Majestic",
        "service_type": "police_station"
    }
    response = client.post("/api/sos", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["is_emergency"] is True
    assert data["emergency_type"] == "police_station"
    # Upparpet Police Station is in Majestic
    assert data["destination"] == "Upparpet Police Station"

def test_map_image_generation():
    response = client.get("/api/route/map-image?origin=Majestic&destination=MG+Road&criteria=distance")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # PNG signature check
    assert response.content.startswith(b"\x89PNG")

def test_traffic_api_and_reload():
    response = client.get("/api/traffic")
    assert response.status_code == 200
    delays = response.json()
    assert len(delays) > 0

    reload_resp = client.post("/api/traffic/reload")
    assert reload_resp.status_code == 200
    assert reload_resp.json()["records_loaded"] == len(delays)

def test_history_logging():
    # Make a route query
    client.post("/api/route", json={"origin": "MG Road", "destination": "Indiranagar", "criteria": "distance"})
    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) > 0
    assert any(h["origin_name"] == "MG Road" for h in history)
