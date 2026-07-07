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


def test_data_health_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.build_data_health",
        lambda: {
            "overall_status": "degraded",
            "summary": "mock health",
            "sources": [
                {
                    "name": "DeepSeek AI Coach",
                    "status": "fallback",
                    "detail": "mock",
                    "live_data": False,
                    "fallback_available": True,
                }
            ],
        },
    )

    response = TestClient(app).get("/data/health")

    assert response.status_code == 200
    assert response.json()["overall_status"] == "degraded"
    assert response.json()["sources"][0]["name"] == "DeepSeek AI Coach"
