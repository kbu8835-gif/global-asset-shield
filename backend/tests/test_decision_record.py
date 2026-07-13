from fastapi.testclient import TestClient

from app import app
from database import get_connection, init_db
from immune.decision_record import list_decision_records


client = TestClient(app)


def test_legacy_investment_journal_mirrors_into_decision_records_and_notebook():
    init_db()
    asset = "PYMODEL"
    with get_connection() as conn:
        conn.execute("DELETE FROM journal_entries WHERE asset = ?", (asset,))
        conn.execute("DELETE FROM investment_journal_entries WHERE asset_symbol = ?", (asset,))
        conn.commit()

    response = client.post(
        "/journal/create",
        json={
            "user_id": "demo_user",
            "asset_symbol": asset,
            "asset_type": "crypto",
            "action": "consider_buy after pump",
            "reason": "最近涨很多，我怕踏空，想先记录",
            "emotion_tag": "FOMO",
            "risk_score": 82,
            "ai_advice": "不建议买",
            "user_decision": "still_buy",
        },
    )

    assert response.status_code == 200
    records = list_decision_records("demo_user")
    assert any(record.asset == asset for record in records)

    notebook_response = client.get("/notebook")
    assert notebook_response.status_code == 200
    assert any(item["asset"] == asset and item["entry_type"] == "investment_journal" for item in notebook_response.json())

    dna_response = client.get("/dna")
    assert dna_response.status_code == 200
    assert "FOMO/追涨相关表达" in dna_response.json()["summary"]
