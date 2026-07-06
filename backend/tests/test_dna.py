from fastapi.testclient import TestClient

from app import app


def test_get_dna_returns_investment_profile():
    response = TestClient(app).get("/dna")

    assert response.status_code == 200
    data = response.json()
    assert data["investor_type"]
    assert 0 <= data["discipline"] <= 100
    assert 0 <= data["patience"] <= 100
    assert 0 <= data["risk_appetite"] <= 100
    assert 0 <= data["emotion_control"] <= 100
    assert 0 <= data["independent_thinking"] <= 100
    assert data["summary"]
