from fastapi.testclient import TestClient

from app import app


def test_root_health():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Global Asset Shield Agent",
        "version": "V1.0 Beta",
        "concept": "AI Investment Immune System",
        "status": "running",
    }


def test_health_endpoint_reports_database():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
        "version": "V1.0 Beta",
    }
