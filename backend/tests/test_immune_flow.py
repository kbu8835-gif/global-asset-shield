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
    assert data["historical_dna_scan"]["available"] is True


def test_immune_report_uses_historical_dna_patterns(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 45,
            "risk_level": "中风险",
            "risk_reasons": ["mock"],
            "raw_data": {"asset": asset},
        },
    )
    client.post(
        "/immune/report",
        json={
            "asset": "HISTORYFOMO",
            "asset_type": "crypto",
            "user_intent": "涨很多了怕踏空",
            "user_text": "已经涨很多，我怕踏空，准备重仓",
            "buy_reason": "感觉马上起飞",
            "risk_awareness": "不清楚风险",
            "worst_case_plan": "跌了就再看看",
            "position_size": "50%",
            "horizon": "短线",
        },
    )

    response = client.post(
        "/immune/report",
        json={
            "asset": "HISTORYFOMO2",
            "asset_type": "crypto",
            "user_intent": "涨很多了怕踏空",
            "user_text": "又涨了很多，我怕错过",
            "buy_reason": "想追一下",
            "risk_awareness": "不清楚",
            "worst_case_plan": "再看看",
            "position_size": "50%",
            "horizon": "短线",
        },
    )

    assert response.status_code == 200
    data = response.json()
    history = data["historical_dna_scan"]
    assert history["available"] is True
    assert history["triggered_patterns"]
    assert history["risk_adjustment"] > 0
    assert "历史 DNA" in data["summary"]
    assert "历史重复模式" in data["decision_reason"]


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


def test_immune_report_supports_short_direction(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_stock",
        lambda asset: {
            "risk_score": 45,
            "risk_level": "中风险",
            "risk_reasons": ["mock stock"],
            "raw_data": {"symbol": asset, "price": 300, "market_cap": 1_000_000_000, "pe": 60},
        },
    )
    response = client.post(
        "/immune/report",
        json={
            "asset": "TSLA",
            "asset_type": "stock",
            "trade_direction": "short",
            "user_intent": "自己研究",
            "user_text": "我想做空 TSLA，觉得它一定会跌，涨了我就止损",
            "buy_reason": "估值太高，想做空",
            "risk_awareness": "可能被逼空",
            "worst_case_plan": "上涨 10% 就止损",
            "position_size": "5%",
            "horizon": "短线",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["trade_direction"] == "short"
    assert data["final_decision"] in {"🔴 Don't Short", "🟡 Wait", "🟢 Small Short"}
    assert any("逼空" in item for item in data["devil_advocate"]["against_buying"])
    assert any(item["bias_type"] == "Short Bias" for item in data["bias_detection"]["biases"])


def test_immune_report_personalizes_advanced_sections(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 55,
            "risk_level": "中风险",
            "risk_reasons": ["mock crypto"],
            "raw_data": {"asset": asset, "price_usd": "0.01", "liquidity": 100000, "volume24h": 10},
        },
    )
    response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "trade_direction": "short",
            "user_intent": "自己研究",
            "user_text": "我想做空 PEPE，但会按计划执行",
            "buy_reason": "涨太快，成交量没有跟上",
            "risk_awareness": "可能被逼空",
            "favorable_plan": "下跌20%止盈",
            "sideways_plan": "横盘 3 天重新评估",
            "worst_case_plan": "上涨 10% 就止损",
            "position_size": "ALL IN",
            "horizon": "短线",
        },
    )

    assert response.status_code == 200
    data = response.json()
    devil_text = " ".join(data["devil_advocate"]["against_buying"])
    regret_text = " ".join(data["regret_simulation"].values())
    munger_paths = " ".join(data["munger_lens"]["inversion"]["failure_paths"])

    assert "ALL IN" in devil_text
    assert "下跌20%止盈" in devil_text
    assert "上涨 10% 就止损" in regret_text
    assert "横盘 3 天重新评估" in munger_paths


def test_immune_report_watch_direction_returns_observation_plan(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 42,
            "risk_level": "中风险",
            "risk_reasons": ["mock crypto"],
            "raw_data": {"asset": asset, "price_usd": "0.01", "liquidity": 100000, "volume24h": 20000},
        },
    )
    response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "trade_direction": "watch",
            "user_intent": "涨很多了怕踏空",
            "user_text": "我先观察 PEPE，不想追高",
            "buy_reason": "等成交量和流动性确认",
            "risk_awareness": "成交量和流动性改善",
            "worst_case_plan": "不追，重新扫描",
            "position_size": "5%",
            "horizon": "24小时",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["trade_direction"] == "watch"
    assert data["final_decision"] == "🟡 Wait"
    assert data["observation_plan"]["signal_to_watch"] == "成交量和流动性改善"
    assert "观望" in data["observation_plan"]["summary"]
