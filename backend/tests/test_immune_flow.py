from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_returns_v1_beta():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "V1.0 Beta"
    assert response.json()["concept"] == "AI Investment Immune System"


def test_immune_report_fomo_saves_journal(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 40,
            "risk_level": "中风险",
            "risk_reasons": ["mock"],
            "raw_data": {"asset": asset},
        },
    )
    payload = {
        "asset": "PEPE",
        "asset_type": "crypto",
        "user_intent": "涨很多了怕错过",
        "user_text": "这个币已经涨了40%，我怕踏空，想梭哈",
        "buy_reason": "看到KOL推荐，感觉马上要起飞",
        "risk_awareness": "不太清楚风险",
        "worst_case_plan": "跌了就再看看",
        "position_size": "50%",
        "horizon": "短线",
    }

    response = client.post("/immune/report", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert any(item["bias_type"] == "FOMO" for item in data["bias_detection"]["biases"])
    assert data["emotion_scan"]["emotion_score"] > 0
    assert data["final_decision"]
    assert data["journal_saved"] is True


def test_immune_report_kol_all_in_wait_or_dont_buy(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 50,
            "risk_level": "中风险",
            "risk_reasons": ["mock"],
            "raw_data": {"asset": asset},
        },
    )
    payload = {
        "asset": "DOGE",
        "asset_type": "crypto",
        "user_intent": "KOL推荐",
        "user_text": "KOL推荐，准备梭哈",
        "buy_reason": "KOL推荐，群里说马上起飞",
        "risk_awareness": "不清楚风险",
        "worst_case_plan": "跌了就再看看",
        "position_size": "全部",
        "horizon": "短线",
    }

    response = client.post("/immune/report", json=payload)
    data = response.json()
    bias_types = {item["bias_type"] for item in data["bias_detection"]["biases"]}

    assert response.status_code == 200
    assert "Authority Bias" in bias_types or "KOL 驱动" in data["emotion_scan"]["detected_emotions"]
    assert data["final_decision"] in {"🔴 Don't Buy", "🟡 Wait"}
