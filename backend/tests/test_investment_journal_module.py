from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_investment_journal_create_dna_health_and_outcome():
    user_id = "pytest_investor"
    create_response = client.post(
        "/journal/create",
        json={
            "user_id": user_id,
            "asset_symbol": "PEPE",
            "asset_type": "crypto",
            "action": "consider_buy after pump",
            "reason": "KOL 推荐，最近涨很多",
            "emotion_tag": "FOMO",
            "risk_score": 78,
            "ai_advice": "不建议买",
            "user_decision": "still_buy",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["journal_entry_id"] > 0
    assert created["behavior_risk_score"] == 100
    assert created["ai_summary"]

    list_response = client.get(f"/journal/{user_id}")
    assert list_response.status_code == 200
    assert list_response.json()[0]["asset_symbol"] == "PEPE"

    dna_response = client.get(f"/journal/dna/{user_id}")
    assert dna_response.status_code == 200
    assert dna_response.json()["fomo_score"] > 0
    assert dna_response.json()["kol_dependency_score"] > 0

    health_response = client.get(f"/journal/health/{user_id}")
    assert health_response.status_code == 200
    assert "health_score" in health_response.json()
    assert health_response.json()["summary"]

    outcome_response = client.post(
        "/journal/outcome",
        json={
            "journal_entry_id": created["journal_entry_id"],
            "outcome_7d": "-12%",
            "outcome_30d": "-38%",
            "user_feedback": "当时太冲动了",
            "ai_was_right": True,
        },
    )
    assert outcome_response.status_code == 200
    assert outcome_response.json()["updated_dna"]["discipline_score"] >= dna_response.json()["discipline_score"]
    assert outcome_response.json()["behavior_summary"]
