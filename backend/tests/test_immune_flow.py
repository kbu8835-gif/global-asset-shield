from fastapi.testclient import TestClient
import pytest

from app import app
from immune.natural_language import build_request_from_loose_payload


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_llm_network(monkeypatch):
    monkeypatch.setattr("immune.llm.DEEPSEEK_API_KEY", "")


def test_health_returns_v1_beta():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "V1.0 Beta"
    assert response.json()["concept"] == "AI Investment Immune System"


def test_immune_report_empty_payload_returns_usage_guide():
    response = client.post("/immune/report", json={})
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "needs_user_input"
    assert data["okx_ai_agent_result"]["recommended_display_field"] == "okx_ai_agent_result.display_markdown"
    assert data["okx_agent_protocol"]["pre_call_required"] is True
    assert "交易想法" in data["message"]
    assert "usage_instruction" in data
    assert "next_user_template" in data
    assert "trade_idea_examples" in data
    assert len(data["trade_idea_examples"]) >= 3
    assert "OKX.AI 推荐调用模板" in data["usage_instruction"]
    assert "请只复制下面" in data["usage_instruction"]
    assert "OKX.AI 推荐调用模板" not in data["next_user_template"]
    assert "请复制" not in data["next_user_template"]
    assert "这里改成你的交易想法" in data["next_user_template"]
    assert "okx_market_data" in data["next_user_template"]
    assert "先用 OKX 查询" in data["okx_ai_agent_result"]["caller_instruction"]
    assert "你现在只需要做一件事" in data["okx_ai_agent_result"]["display_markdown"]
    assert "可复制模板" in data["okx_ai_agent_result"]["display_markdown"]
    assert "```text" in data["okx_ai_agent_result"]["display_markdown"]
    assert "交易想法可以这样写" in data["okx_ai_agent_result"]["display_markdown"]
    assert "接下来 Agent 会做什么" in data["okx_ai_agent_result"]["display_markdown"]
    assert "这里只改成你的交易想法" not in data["okx_ai_agent_result"]["display_markdown"]
    assert "这里改成你的交易想法" in data["okx_ai_agent_result"]["display_markdown"]
    assert "我想买 PEPE" in data["okx_ai_agent_result"]["display_markdown"]


def test_immune_report_parses_natural_language_query(monkeypatch):
    monkeypatch.setattr(
        "immune.risk.scan_crypto",
        lambda asset: {
            "risk_score": 45,
            "risk_level": "中风险",
            "risk_reasons": ["mock"],
            "raw_data": {"asset": asset},
        },
    )

    response = client.post(
        "/immune/report",
        json={"query": "我想买 PEPE，看到 KOL 推荐，准备 50% 仓位，跌 10% 止损。"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["asset"] == "PEPE"
    assert data["asset_type"] == "crypto"
    assert data["trade_direction"] == "long"
    assert data["okx_ai_agent_result"]["mini_notebook"]["what_user_wrote"]["position_size"] == "50%"
    assert any("KOL" in item for item in data["emotion_scan"]["detected_emotions"])
    assert data["final_decision"]
    next_action = data["okx_ai_agent_result"]["okx_agent_next_action"]
    assert next_action["required"] is True
    assert next_action["action"] == "query_okx_market_data_and_retry"
    assert "external_market_data" in next_action["message"]
    assert "OKX Agent 下一步" in data["okx_ai_agent_result"]["display_markdown"]


def test_natural_language_parser_understands_common_trade_phrases():
    payload = build_request_from_loose_payload(
        {
            "query": "我想做多 BTC，担心追高，准备小仓位，涨20%减仓，横盘3天重新评估，跌破关键位置就退出。"
        }
    )

    assert payload is not None
    assert payload.asset == "BTC"
    assert payload.asset_type == "crypto"
    assert payload.trade_direction == "long"
    assert payload.position_size == "5%"
    assert payload.worst_case_plan == "跌破关键位置就退出"
    assert payload.favorable_plan == "上涨 20% 就减仓"
    assert payload.sideways_plan == "横盘 3 天后重新评估"
    assert "担心追高" in payload.risk_awareness


def test_natural_language_parser_understands_short_trade_phrases():
    payload = build_request_from_loose_payload(
        {
            "query": "我想做空 NVDA，觉得估值太贵，准备三成仓，下跌15%止盈，横盘一周平仓，反弹8%就止损。"
        }
    )

    assert payload is not None
    assert payload.asset == "NVDA"
    assert payload.asset_type == "stock"
    assert payload.trade_direction == "short"
    assert payload.position_size == "30%"
    assert payload.worst_case_plan == "上涨 8% 就止损"
    assert payload.favorable_plan == "下跌 15% 就止盈"
    assert payload.sideways_plan == "横盘 一 周后重新评估"
    assert "估值太贵" in payload.risk_awareness


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
    assert any("50%" in question for question in data["conviction_score"]["improvement_questions"])
    assert data["ai_coach"]["fallback_used"] is True
    assert data["ai_coach"]["coach_message"]
    assert data["data_confidence"]["score"] < 50
    assert data["data_confidence"]["level"] in {"Low Confidence", "Very Low Confidence"}
    assert data["ai_coach"]["data_confidence_note"]
    assert data["munger_lens"]["framework"] == "Munger Lens"
    assert data["munger_lens"]["munger_verdict"] in {"No", "Too Hard", "Small Bet"}
    assert data["historical_dna_scan"]["available"] is True
    assert data["okx_ai_agent_result"]["designed_for"] == "OKX.AI A2MCP"
    assert data["okx_ai_agent_result"]["decision"] == data["final_decision"]
    assert data["okx_ai_agent_result"]["mini_notebook"]["what_user_wrote"]["position_size"] == "50%"
    assert data["okx_ai_agent_result"]["must_answer_before_trade"]
    assert data["okx_ai_agent_result"]["recommended_display_field"] == "okx_ai_agent_result.display_markdown"
    assert data["okx_ai_agent_result"]["short_answer"].startswith(data["final_decision"])
    assert "# " in data["okx_ai_agent_result"]["display_markdown"]
    assert "## 市场数据" in data["okx_ai_agent_result"]["display_markdown"]
    assert "## 下单前必须回答" in data["okx_ai_agent_result"]["display_markdown"]


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
    assert history["warnings"]
    assert history["risk_adjustment"] >= 0
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


def test_immune_report_accepts_external_okx_market_data(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: None)
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not fallback")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)

    response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "trade_direction": "long",
            "user_intent": "KOL推荐",
            "user_text": "看到KOL推荐，最近涨很多，怕错过",
            "buy_reason": "KOL推荐，感觉马上起飞",
            "risk_awareness": "不太清楚",
            "worst_case_plan": "跌10%止损",
            "position_size": "50%",
            "horizon": "短线",
            "external_market_data": {
                "source": "OKX Onchain OS Agent",
                "symbol": "PEPE",
                "price": 0.000002741,
                "market_cap": 1_130_000_000,
                "liquidity": 20_490_000,
                "volume24h": 740_190,
                "holders": 568_148,
                "risk_control_level": 2,
                "top10_hold_percent": 8.0739,
                "is_honeypot": False,
                "is_blacklisted": False,
                "is_mintable": False,
                "is_proxy": False,
                "owner_privilege": "low",
                "buy_tax": 0,
                "sell_tax": 0,
                "liquidity_change_24h": -3.2,
                "pool_depth_warning": False,
                "okx_url": "https://www.okx.com/web3/dex/pepe",
            },
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["risk_scan"]["raw_data"]["primary_data_source"] == "external_okx_agent"
    assert data["risk_scan"]["raw_data"]["external_market_data_used"] is True
    assert data["okx_ai_agent_result"]["okx_agent_next_action"]["required"] is False
    assert data["risk_scan"]["raw_data"]["security_source"] == "OKX Onchain OS Agent"
    assert "调用方 Agent 传入的 OKX 链上行情" in " ".join(data["risk_scan"]["risk_reasons"])
    assert "OKX 合约安全数据" in " ".join(data["risk_scan"]["risk_reasons"])
    assert "OKX Onchain OS Agent" in data["okx_ai_agent_result"]["market_snapshot"]
    assert data["okx_ai_agent_result"]["market_link"] == "https://www.okx.com/web3/dex/pepe"
    assert "交易对链接" not in data["data_confidence"]["missing"]
    assert "https://www.okx.com/web3/dex/pepe" in data["okx_ai_agent_result"]["display_markdown"]
    assert "OKX 链上行情" in data["okx_ai_agent_result"]["display_markdown"]


def test_immune_report_accepts_okx_market_data_alias_with_chinese_fields(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_public_ticker", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call public ticker")))
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call cli")))
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not fallback")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)

    response = client.post(
        "/immune/report",
        json={
            "asset": "PEPE",
            "asset_type": "crypto",
            "trade_direction": "long",
            "user_intent": "KOL推荐",
            "user_text": "看到KOL推荐，最近涨很多，怕错过",
            "buy_reason": "KOL推荐，感觉马上起飞",
            "risk_awareness": "不太清楚",
            "worst_case_plan": "价格下跌 10% 执行止损",
            "position_size": "50%",
            "okx_market_data": {
                "数据源": "OKX OnchainOS Agent",
                "币种": "PEPE",
                "价格": "$0.0000028542",
                "市值": "$1.18B",
                "流动性": "$21.75M",
                "24h成交量": "$810.6K",
                "持有人": "568,460",
                "风险控制等级": "2",
                "Top10 持仓占比": "8.0816%",
                "合约地址": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
                "交易池链接": "https://www.okx.com/web3/dex/pepe",
            },
        },
    )

    data = response.json()
    raw = data["risk_scan"]["raw_data"]

    assert response.status_code == 200
    assert raw["external_market_data_used"] is True
    assert raw["primary_data_source"] == "external_okx_agent"
    assert raw["price_usd"] == 0.0000028542
    assert raw["fdv"] == 1_180_000_000
    assert raw["liquidity"] == 21_750_000
    assert raw["volume24h"] == 810_600
    assert raw["pair_url"] == "https://www.okx.com/web3/dex/pepe"
    assert data["okx_ai_agent_result"]["okx_agent_next_action"]["required"] is False
    assert "OKX OnchainOS Agent" in data["okx_ai_agent_result"]["market_snapshot"]


def test_immune_report_parses_okx_market_data_text_alias(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_public_ticker", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call public ticker")))
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call cli")))
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not fallback")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)

    response = client.post(
        "/immune/report",
        json={
            "query": "我想买 PEPE，看到 KOL 推荐，准备 50% 仓位，跌 10% 止损。",
            "okx_query_result": """
            PEPE 以太坊合约：0x6982508145454ce325ddbe47a25d4ec3d2311933
            价格：约 $0.0000028542
            市值：约 $1.18B
            流动性：约 $21.75M
            24h 成交量：约 $810.6K
            持有人：568,460
            风险控制等级：2
            Top10 持仓占比：8.0816%
            https://www.okx.com/web3/dex/pepe
            """,
        },
    )

    data = response.json()
    raw = data["risk_scan"]["raw_data"]

    assert response.status_code == 200
    assert raw["external_market_data_used"] is True
    assert raw["primary_data_source"] == "external_okx_agent"
    assert raw["price_usd"] == 0.0000028542
    assert raw["liquidity"] == 21_750_000
    assert raw["volume24h"] == 810_600
    assert raw["okx_onchain"]["holders"] == 568_460
    assert data["okx_ai_agent_result"]["okx_agent_next_action"]["required"] is False


def test_immune_report_accepts_external_okx_stock_market_data(monkeypatch):
    monkeypatch.setattr("scanner.stock.fetch_us_stock", lambda _symbol: (_ for _ in ()).throw(RuntimeError("should not call yfinance")))
    monkeypatch.setattr(
        "scanner.stock.fetch_yahoo_chart_stock",
        lambda _symbol: (_ for _ in ()).throw(RuntimeError("should not call yahoo")),
    )

    response = client.post(
        "/immune/report",
        json={
            "asset": "NVDA",
            "asset_type": "stock",
            "trade_direction": "long",
            "user_intent": "自己研究",
            "user_text": "我想做多 NVDA，但担心已经涨太多",
            "buy_reason": "AI 芯片增长强",
            "risk_awareness": "估值和业绩预期风险",
            "worst_case_plan": "跌破计划就止损",
            "position_size": "10%",
            "horizon": "中线",
            "external_market_data": {
                "source": "OKX Market Agent",
                "symbol": "NVDA",
                "price": 172.5,
                "market_cap": 4_200_000_000_000,
                "day_change_percent": 9.2,
                "volume": 80_000_000,
                "average_volume": 40_000_000,
                "pe": 88,
                "revenue_growth": 0.65,
                "profit_margin": 0.52,
                "debt_to_equity": 35,
                "free_cash_flow": 40_000_000_000,
                "recommendation_key": "buy",
            },
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["risk_scan"]["raw_data"]["data_source"] == "okx_market_agent"
    assert data["risk_scan"]["raw_data"]["external_market_data_used"] is True
    assert "OKX Market Agent 美股行情" in " ".join(data["risk_scan"]["risk_reasons"])
    assert "OKX Market Agent" in data["okx_ai_agent_result"]["market_snapshot"]
    assert "数据源：OKX Market Agent" in data["okx_ai_agent_result"]["display_markdown"]


def test_immune_report_treats_external_okx_spot_as_high_confidence(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_public_ticker", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call public ticker")))
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call cli")))
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not fallback")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: (_ for _ in ()).throw(RuntimeError("should not call goplus")))

    response = client.post(
        "/immune/report",
        json={
            "asset": "ETH",
            "asset_type": "crypto",
            "trade_direction": "short",
            "user_intent": "自己研究",
            "user_text": "我想做空eth，现在是下跌趋势，准备30%仓位，跌10%继续补仓",
            "buy_reason": "现在是下跌趋势",
            "risk_awareness": "担心趋势继续",
            "worst_case_plan": "跌10%继续补仓",
            "position_size": "30%",
            "okx_market_data": {
                "source": "OKX Market + OKX OnchainOS",
                "symbol": "ETH",
                "instId": "ETH-USDT",
                "last": "1924",
                "volCcy24h": "509424899",
                "riskLevel": "LOW",
            },
        },
    )

    data = response.json()
    raw = data["risk_scan"]["raw_data"]

    assert response.status_code == 200
    assert raw["external_market_data_used"] is True
    assert raw["primary_data_source"] == "okx_public_market"
    assert raw["is_cex_market_data"] is True
    assert data["data_confidence"]["level"] == "High Confidence"
    assert data["data_confidence"]["score"] == 100
    assert "OKX 市场行情" in " ".join(data["risk_scan"]["risk_reasons"])
    assert "合约安全" not in data["data_confidence"]["missing"]


def test_okx_ai_result_surfaces_external_okx_security_scan(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: None)
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not fallback")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)

    response = client.post(
        "/immune/report",
        json={
            "asset": "RISKY",
            "asset_type": "crypto",
            "trade_direction": "long",
            "user_intent": "KOL推荐",
            "user_text": "看到KOL推荐，怕错过",
            "buy_reason": "KOL推荐",
            "risk_awareness": "不清楚",
            "worst_case_plan": "跌10%止损",
            "position_size": "50%",
            "horizon": "短线",
            "external_market_data": {
                "source": "OKX Onchain OS Agent",
                "symbol": "RISKY",
                "price": 0.01,
                "market_cap": 20_000_000,
                "liquidity": 40_000,
                "volume24h": 5_000,
                "holders": 100,
                "risk_control_level": 4,
                "top10_hold_percent": 55,
                "is_honeypot": True,
                "is_blacklisted": True,
                "is_mintable": True,
                "is_proxy": True,
                "owner_privilege": "high",
                "buy_tax": 12,
                "sell_tax": 15,
                "liquidity_change_24h": -35,
                "pool_depth_warning": True,
            },
        },
    )

    data = response.json()
    security_scan = data["okx_ai_agent_result"]["okx_security_scan"]
    display = data["okx_ai_agent_result"]["display_markdown"]

    assert response.status_code == 200
    assert security_scan["honeypot"] is True
    assert security_scan["blacklist"] is True
    assert security_scan["owner_privilege"] == "high"
    assert security_scan["buy_tax_percent"] == 12
    assert security_scan["sell_tax_percent"] == 15
    assert "OKX 安全扫描" in display
    assert "疑似蜜罐：是" in display
    assert "黑名单风险：是" in display
    assert "买税/卖税：12% / 15%" in display
