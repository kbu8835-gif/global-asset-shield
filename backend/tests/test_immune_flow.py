from fastapi.testclient import TestClient
import pytest

from app import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_llm_network(monkeypatch):
    monkeypatch.setattr("immune.llm.DEEPSEEK_API_KEY", "")


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
    assert data["ai_coach"]["fallback_used"] is True
    assert data["ai_coach"]["coach_message"]
    assert data["data_confidence"]["score"] < 50
    assert data["data_confidence"]["level"] in {"Low Confidence", "Very Low Confidence"}
    assert data["ai_coach"]["data_confidence_note"]
    assert data["munger_lens"]["framework"] == "Munger Lens"
    assert data["munger_lens"]["munger_verdict"] in {"No", "Too Hard", "Small Bet"}


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
    assert "KOL" in data["munger_lens"]["incentive_check"]


def test_immune_report_supports_cn_stock(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_cn_stock",
        lambda asset: {
            "risk_score": 55,
            "risk_level": "中风险",
            "risk_reasons": ["A股 mock"],
            "raw_data": {"symbol": asset, "name": "贵州茅台", "fallback_mock": True},
        },
    )
    response = client.post(
        "/immune/report",
        json={
            "asset": "600519",
            "asset_type": "cn_stock",
            "user_intent": "自己研究",
            "user_text": "我想看看贵州茅台现在是否适合买",
            "buy_reason": "自己研究后关注",
            "risk_awareness": "估值和消费需求风险",
            "worst_case_plan": "跌破计划就退出",
            "position_size": "5%",
            "horizon": "中线",
        },
    )

    assert response.status_code == 200
    assert response.json()["asset_type"] == "cn_stock"
    assert response.json()["risk_scan"]["raw_data"]["name"] == "贵州茅台"
    assert response.json()["data_confidence"]["score"] < 50
