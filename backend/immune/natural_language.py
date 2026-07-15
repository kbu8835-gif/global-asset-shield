import re
from typing import Any, Dict, Optional

from schemas import ImmuneReportRequest


STOCK_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "MSTR", "GME", "AMC"}
CRYPTO_HINTS = {"PEPE", "BTC", "ETH", "SOL", "DOGE", "SHIB", "BNB", "XRP", "ARB", "OP", "MEME"}


def build_report_usage_guide() -> Dict[str, Any]:
    display_markdown = "\n".join(
        [
            "# Global Asset Shield 已准备好",
            "",
            "## 给 OKX Agent 的调用协议",
            "在正式调用投资免疫扫描前，请先用 OKX 查询目标资产的最新市场数据。",
            "",
            "调用顺序：",
            "1. 先询问用户一句交易想法。",
            "2. 从交易想法里识别资产、资产类型和方向。",
            "3. 使用 OKX 市场 / DEX / OnchainOS 能力查询该资产最新数据。",
            "4. 将 OKX 查询结果作为 `external_market_data` 传给本接口。",
            "5. 最终优先展示 `okx_ai_agent_result.display_markdown`。",
            "",
            "请用一句话告诉我你的交易想法，例如：",
            "",
            "“我想买 PEPE，看到 KOL 推荐，准备 50% 仓位，跌 10% 止损。”",
            "",
            "或者：",
            "",
            "“我想做空 NVDA，觉得涨太多了，仓位 10%，上涨 8% 就止损。”",
            "",
            "我会帮你检测：",
            "- OKX 市场数据",
            "- OKX 安全扫描",
            "- 情绪冲动",
            "- KOL / FOMO / 仓位风险",
            "- 下单前必须回答的问题",
            "",
            "这不是预测价格的工具。它帮你在下单前停一下，在复盘后变聪明一点。",
        ]
    )
    return {
        "status": "needs_user_input",
        "service_name": "Investment Immune Scan",
        "message": "请补充一句你的交易想法。调用方 Agent 应先查询 OKX 市场数据，并作为 external_market_data 传入本接口。",
        "okx_agent_protocol": {
            "role": "caller_instruction",
            "pre_call_required": True,
            "instruction": "先使用 OKX 查询目标资产的最新市场数据，再调用 /immune/report。",
            "workflow": [
                "Ask the user for one sentence describing the trade idea.",
                "Extract asset, asset_type, trade_direction, position_size, risk_awareness, and worst_case_plan.",
                "Query OKX market / DEX / OnchainOS data for the asset.",
                "Pass OKX result as external_market_data.",
                "Display okx_ai_agent_result.display_markdown first.",
            ],
            "external_market_data_schema": {
                "source": "OKX Market Agent or OKX Onchain OS Agent",
                "symbol": "BTC",
                "price": 0,
                "market_cap": 0,
                "liquidity": 0,
                "volume24h": 0,
                "holders": 0,
                "risk_control_level": 0,
                "top10_hold_percent": 0,
                "pair_url": "https://www.okx.com/...",
            },
        },
        "examples": [
            "我想买 PEPE，看到 KOL 推荐，准备 50% 仓位，跌 10% 止损。",
            "我想做空 NVDA，觉得涨太多了，仓位 10%，上涨 8% 就止损。",
        ],
        "okx_ai_agent_result": {
            "decision": "Need Input",
            "caller_instruction": "请先用 OKX 查询用户目标资产的最新市场数据，并作为 external_market_data 传入 /immune/report。",
            "recommended_display_field": "okx_ai_agent_result.display_markdown",
            "display_markdown": display_markdown,
        },
    }


def _text_from_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("query", "message", "text", "user_text", "prompt", "input"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_asset(text: str) -> Optional[str]:
    upper_text = text.upper()
    for symbol in sorted(STOCK_SYMBOLS | CRYPTO_HINTS, key=len, reverse=True):
        if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", upper_text):
            return symbol
    match = re.search(r"\b[A-Z]{2,6}\b", upper_text)
    return match.group(0) if match else None


def _asset_type(asset: str, text: str) -> str:
    upper_asset = asset.upper()
    if upper_asset in STOCK_SYMBOLS or any(word in text for word in ("美股", "股票", "股价")):
        return "stock"
    if re.fullmatch(r"\d{6}", upper_asset):
        return "cn_stock"
    return "crypto"


def _trade_direction(text: str) -> str:
    if any(word in text for word in ("做空", "开空", "空", "short", "Short")):
        return "short"
    return "long"


def _intent(text: str) -> str:
    upper_text = text.upper()
    if any(word in upper_text for word in ("KOL", "大V", "博主", "喊单", "老师")):
        return "KOL推荐"
    if "朋友" in text:
        return "朋友推荐"
    if any(word in text for word in ("怕踏空", "错过", "涨太多", "涨很多", "上车")):
        return "涨很多了怕踏空"
    if any(word in text for word in ("抄底", "补仓", "回本")):
        return "抄底补仓"
    return "自己研究"


def _position_size(text: str) -> Optional[str]:
    match = re.search(r"(\d{1,3})\s*%", text)
    if match:
        return f"{match.group(1)}%"
    if any(word in text for word in ("ALL IN", "all in", "梭哈", "满仓", "全部")):
        return "ALL IN"
    if "半仓" in text:
        return "50%"
    if "重仓" in text:
        return "50%"
    return None


def _worst_case_plan(text: str, direction: str) -> Optional[str]:
    if direction == "short":
        match = re.search(r"(上涨|涨|反弹)\s*(\d{1,3})\s*%\s*(就)?\s*(止损|平仓|认错)", text)
        if match:
            return f"上涨 {match.group(2)}% 就{match.group(4)}"
    match = re.search(r"(下跌|跌|回撤)\s*(\d{1,3})\s*%\s*(就)?\s*(止损|卖出|退出)", text)
    if match:
        return f"跌 {match.group(2)}% 就{match.group(4)}"
    if "止损" in text:
        return "按用户描述止损"
    return None


def build_request_from_loose_payload(payload: Any) -> Optional[ImmuneReportRequest]:
    if isinstance(payload, dict) and payload.get("asset") and payload.get("asset_type"):
        return ImmuneReportRequest(**payload)

    text = _text_from_payload(payload)
    if not text:
        return None
    asset = _extract_asset(text)
    if not asset:
        return None

    direction = _trade_direction(text)
    return ImmuneReportRequest(
        asset=asset,
        asset_type=_asset_type(asset, text),
        trade_direction=direction,
        user_intent=_intent(text),
        user_text=text,
        buy_reason=text,
        risk_awareness="未填写，系统将按风险意识不足处理",
        worst_case_plan=_worst_case_plan(text, direction),
        position_size=_position_size(text),
        horizon="短线" if any(word in text for word in ("短线", "今天", "明天", "马上")) else None,
    )
