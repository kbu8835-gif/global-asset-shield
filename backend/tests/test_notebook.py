from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_notebook_crud_review_and_coach():
    create_response = client.post(
        "/notebook",
        json={
            "asset": "BTC",
            "asset_type": "crypto",
            "title": "BTC thesis",
            "decision": "Wait",
            "notes": "Watching the breakout.",
            "buy_reason": "I think momentum is improving.",
            "worst_case_plan": "Exit if thesis breaks.",
            "risk_awareness": "Volatility and liquidity.",
            "position_size": "5%",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    notebook_id = created["id"]
    assert created["ai_coach"]

    list_response = client.get("/notebook")
    assert list_response.status_code == 200
    assert any(item["id"] == notebook_id for item in list_response.json())

    update_response = client.put(
        f"/notebook/{notebook_id}",
        json={
            "notes": "Updated thesis note.",
            "decision": "Don't Buy",
            "status": "Open",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["notes"] == "Updated thesis note."
    assert updated["decision"] == "Don't Buy"
    assert any(item["event"] == "User Edited" for item in updated["timeline"])

    detail_response = client.get(f"/notebook/{notebook_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "BTC thesis"

    review_response = client.post(
        f"/notebook/{notebook_id}/review",
        json={"current_price": 65000, "user_result_text": "后来我发现没有止损，差点情绪化补仓。"},
    )
    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["status"] == "Reviewed"
    assert reviewed["mistakes"]
    assert reviewed["lesson"]
    assert reviewed["next_action"]
