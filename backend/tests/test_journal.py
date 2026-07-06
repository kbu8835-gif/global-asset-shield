from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_journal_list_and_review(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 45,
            "risk_level": "中风险",
            "risk_reasons": ["mock"],
            "raw_data": {"asset": asset},
        },
    )
    report_response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "user_intent": "KOL推荐",
            "user_text": "怕踏空，想梭哈",
            "buy_reason": "KOL推荐，感觉要起飞",
            "risk_awareness": "不清楚风险",
            "worst_case_plan": "跌了就再看看",
            "position_size": "50%",
            "horizon": "短线",
        },
    )
    journal_id = report_response.json()["report_id"]

    list_response = client.get("/journal")
    detail_response = client.get(f"/journal/{journal_id}")
    review_response = client.post(
        f"/journal/{journal_id}/review",
        json={
            "journal_id": journal_id,
            "current_price": 0.000012,
            "user_result_text": "一个月后亏了28%，我当时太冲动了",
        },
    )

    assert list_response.status_code == 200
    assert any(item["id"] == journal_id for item in list_response.json())
    assert detail_response.status_code == 200
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == "reviewed"
    assert review_response.json()["mistake_type"]

