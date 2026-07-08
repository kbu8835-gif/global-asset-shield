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
    assert reviewed["mistakes"] == "没有止损"
    assert "BTC" not in reviewed["lesson"]
    assert "最坏情况计划" in reviewed["lesson"]
    assert "再看看" in reviewed["next_action"] or "退出条件" in reviewed["next_action"]
    assert "Review:" not in (reviewed["notes"] or "")

    delete_response = client.delete(f"/notebook/{notebook_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    missing_response = client.get(f"/notebook/{notebook_id}")
    assert missing_response.status_code == 404


def test_notebook_review_personalizes_short_squeeze_risk():
    create_response = client.post(
        "/notebook",
        json={
            "asset": "TSLA",
            "asset_type": "stock",
            "trade_direction": "short",
            "title": "TSLA short",
            "decision": "Wait",
            "notes": "Valuation looks stretched.",
            "buy_reason": "I want to short after a fast rally.",
            "worst_case_plan": "If price rises 12%, I close the short.",
            "risk_awareness": "Short squeeze and news risk.",
            "position_size": "5%",
        },
    )
    assert create_response.status_code == 200
    notebook_id = create_response.json()["id"]

    review_response = client.post(
        f"/notebook/{notebook_id}/review",
        json={"current_price": 320, "user_result_text": "结果继续上涨并出现逼空，我差点加空。"},
    )

    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["mistakes"] == "逆势补空"
    assert "上涨后补空" in reviewed["lesson"]
    assert "禁止补空" in reviewed["next_action"]

    client.delete(f"/notebook/{notebook_id}")
