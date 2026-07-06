from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_kol_intelligence_flow_and_integrations(monkeypatch):
    profile_response = client.post(
        "/kol/profiles",
        json={
            "name": "Crypto Rover",
            "twitter_handle": "@rovercrc",
            "youtube_channel": "Crypto Rover",
            "bio": "Crypto market commentator",
        },
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()
    kol_id = profile["id"]

    call_response = client.post(
        "/kol/calls",
        json={
            "kol_id": kol_id,
            "asset": "PEPE",
            "asset_type": "crypto",
            "call_time": "2026-07-01T12:00:00+00:00",
            "call_price": 0.00001,
            "current_price": 0.000012,
            "source": "twitter",
            "source_url": "https://x.com/example/status/123",
            "call_text": "PEPE will 10x. Last chance. 起飞",
            "call_type": "buy",
            "time_horizon": "short",
            "roi_7d": 20,
            "roi_30d": 25,
            "max_drawdown": -12,
        },
    )
    assert call_response.status_code == 200
    call = call_response.json()
    assert call["current_roi"] == 20
    assert "Authority Bias" in call["bias_tags"]

    recalc_response = client.post(f"/kol/profiles/{kol_id}/recalculate")
    assert recalc_response.status_code == 200
    recalculated = recalc_response.json()
    assert recalculated["trust_score"] >= 50
    assert recalculated["total_calls"] >= 1

    dependency_response = client.get("/kol/dependency")
    assert dependency_response.status_code == 200
    assert "kol_dependency" in dependency_response.json()

    dna_response = client.get("/dna")
    assert dna_response.status_code == 200
    assert "kol_dependency" in dna_response.json()
    assert "kol_summary" in dna_response.json()

    immune_response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "user_intent": "KOL推荐",
            "user_text": "Crypto Rover 在 x.com 喊单，PEPE 要起飞，我怕错过",
            "buy_reason": "KOL推荐",
            "risk_awareness": "不太清楚风险",
            "worst_case_plan": "跌了就再看看",
            "position_size": "50%",
            "horizon": "短线",
        },
    )
    assert immune_response.status_code == 200
    kol_scan = immune_response.json()["kol_risk_scan"]
    assert kol_scan["kol_detected"] is True
    assert kol_scan["kol_name"] == "Crypto Rover"

    def fail_price(_asset):
        raise RuntimeError("price down")

    monkeypatch.setattr("immune.kol_intelligence._current_price", fail_price)
    refresh_response = client.post(f"/kol/calls/{call['id']}/refresh")
    assert refresh_response.status_code == 200

    delete_response = client.delete(f"/kol/calls/{call['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

