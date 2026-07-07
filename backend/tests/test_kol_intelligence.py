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

    capture_response = client.post(
        "/kol/capture",
        json={
            "kol_id": kol_id,
            "call_text": "$PEPE will 10x. Last chance before moon. 梭哈起飞",
            "call_price": 0.00001,
            "current_price": 0.000011,
        },
    )
    assert capture_response.status_code == 200
    captured = capture_response.json()
    assert captured["asset"] == "PEPE"
    assert captured["call_type"] == "moonshot"
    assert "FOMO" in captured["emotion_tags"]
    assert "Lottery Bias" in captured["bias_tags"]

    batch_response = client.post(
        "/kol/capture/batch",
        json={
            "kol_id": kol_id,
            "text": "\n".join(
                [
                    "2026-06-30 PEPE 0.00001 PEPE will 10x last chance",
                    "2026-07-03 DOGE 0.12 DOGE moon soon 起飞",
                    "2026-07-06 WIF 1.8 WIF 梭哈 财富自由",
                ]
            ),
        },
    )
    assert batch_response.status_code == 200
    batch = batch_response.json()
    assert batch["created_count"] == 3
    assert batch["kol_risk_profile"]["leek_risk_score"] >= 30
    assert batch["kol_risk_profile"]["profile_type"] in {"FOMO Promoter", "Pump Risk", "Narrative Chaser", "Mixed Record"}

    risk_profile_response = client.get(f"/kol/profiles/{kol_id}/risk-profile")
    assert risk_profile_response.status_code == 200
    assert risk_profile_response.json()["summary"]

    backtest_call_response = client.post(
        "/kol/calls",
        json={
            "kol_id": kol_id,
            "asset": "PEPE",
            "asset_type": "crypto",
            "call_time": "2026-05-01T00:00:00+00:00",
            "call_price": 10,
            "source": "manual",
            "call_text": "PEPE buy",
            "call_type": "buy",
        },
    )
    backtest_call = backtest_call_response.json()
    monkeypatch.setattr("immune.kol_intelligence._current_price", lambda _asset, _asset_type: 14)
    monkeypatch.setattr("immune.kol_intelligence.historical_roi", lambda _asset, _asset_type, _price, _time, days: 15 if days == 7 else 35)
    backtest_refresh = client.post(f"/kol/calls/{backtest_call['id']}/refresh")
    assert backtest_refresh.status_code == 200
    assert backtest_refresh.json()["roi_7d"] == 15
    assert backtest_refresh.json()["roi_30d"] == 35

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

    def fail_price(*_args):
        raise RuntimeError("price down")

    monkeypatch.setattr("immune.kol_intelligence._current_price", fail_price)
    refresh_response = client.post(f"/kol/calls/{call['id']}/refresh")
    assert refresh_response.status_code == 200

    delete_response = client.delete(f"/kol/calls/{call['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
