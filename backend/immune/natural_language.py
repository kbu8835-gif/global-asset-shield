import re
from typing import Any, Dict, Optional

from schemas import ImmuneReportRequest


STOCK_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "MSTR", "GME", "AMC"}
CRYPTO_HINTS = {"PEPE", "BTC", "ETH", "SOL", "DOGE", "SHIB", "BNB", "XRP", "ARB", "OP", "MEME"}

NUMBER_WORDS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


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


EXTERNAL_MARKET_ALIASES = (
    "external_market_data",
    "externalMarketData",
    "okx_data",
    "okxData",
    "okx_market_data",
    "okxMarketData",
    "market_data",
    "marketData",
    "onchain_data",
    "onchainData",
    "token_data",
    "tokenData",
    "okx_query_result",
    "okxQueryResult",
)

MARKET_FIELD_HINTS = {
    "source",
    "provider",
    "symbol",
    "tokenSymbol",
    "price",
    "priceUsd",
    "lastPrice",
    "market_cap",
    "marketCap",
    "marketValue",
    "liquidity",
    "liquidityUsd",
    "liquidityUSD",
    "volume24h",
    "volume24H",
    "volumeUsd24h",
    "24h成交量",
    "24小时成交量",
    "成交量",
    "holders",
    "holderCount",
    "risk_control_level",
    "riskLevelControl",
    "top10_hold_percent",
    "top10HoldPercent",
    "top10HolderRatio",
    "Top10 持仓占比",
    "top10持仓占比",
    "pair_url",
    "poolUrl",
    "okx_url",
    "合约",
    "合约地址",
    "价格",
    "市值",
    "流动性",
    "持有人",
    "风险控制等级",
}


def _to_number_text(value: str) -> Optional[float]:
    cleaned = value.replace(",", "").replace("$", "").strip()
    multiplier = 1.0
    if cleaned.lower().endswith("k"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.lower().endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.lower().endswith("b"):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _parse_market_data_text(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"source": "OKX Agent Text"}
    patterns = {
        "price": r"(?:价格|price)\D{0,8}([0-9][0-9.,]*(?:e-?\d+)?|0?\.\d+)",
        "market_cap": r"(?:市值|market cap|market_cap)\D{0,12}\$?\s*([0-9][0-9.,]*(?:[KMBkmb])?)",
        "liquidity": r"(?:流动性|liquidity)\D{0,12}\$?\s*([0-9][0-9.,]*(?:[KMBkmb])?)",
        "volume24h": r"(?:24h 成交量|24小时成交量|成交量|volume)\D{0,12}\$?\s*([0-9][0-9.,]*(?:[KMBkmb])?)",
        "holders": r"(?:持有人|holders?)\D{0,12}([0-9][0-9,]*)",
        "risk_control_level": r"(?:风险控制等级|risk control level|riskLevelControl)\D{0,8}([0-9]+)",
        "top10_hold_percent": r"(?:Top10 持仓占比|top10 hold|top10HolderRatio|top10HoldPercent)\D{0,12}([0-9.]+)\s*%?",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = _to_number_text(match.group(1))
            if number is not None:
                data[key] = number
    contract = re.search(r"0x[a-fA-F0-9]{40}", text)
    if contract:
        data["contract_address"] = contract.group(0)
    url = re.search(r"https?://[^\s，。；)）]+", text)
    if url:
        data["pair_url"] = url.group(0)
    return data if len(data) > 1 else {}


def _coerce_market_data_candidate(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, str) and value.strip():
        return _parse_market_data_text(value)
    if not isinstance(value, dict):
        return None

    for key in ("data", "result", "market", "token", "token_data", "market_data"):
        nested = value.get(key)
        if isinstance(nested, dict) and any(field in nested for field in MARKET_FIELD_HINTS):
            return nested
        if isinstance(nested, str) and nested.strip():
            parsed = _parse_market_data_text(nested)
            if parsed:
                return parsed

    if any(key in value for key in MARKET_FIELD_HINTS):
        return value
    return None


def _extract_external_market_data(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    for key in EXTERNAL_MARKET_ALIASES:
        parsed = _coerce_market_data_candidate(payload.get(key))
        if parsed:
            return parsed
    nested = payload.get("data") or payload.get("result") or payload.get("market") or payload.get("token")
    if isinstance(nested, str) and nested.strip():
        parsed = _parse_market_data_text(nested)
        if parsed:
            return parsed
    elif isinstance(nested, dict):
        for key in EXTERNAL_MARKET_ALIASES:
            parsed = _coerce_market_data_candidate(nested.get(key))
            if parsed:
                return parsed
        if any(key in nested for key in MARKET_FIELD_HINTS):
            return nested
    if any(key in payload for key in MARKET_FIELD_HINTS):
        return {key: value for key, value in payload.items() if key in MARKET_FIELD_HINTS or key not in {"asset", "asset_type"}}
    return None


def _extract_asset(text: str) -> Optional[str]:
    upper_text = text.upper()
    for symbol in sorted(STOCK_SYMBOLS | CRYPTO_HINTS, key=len, reverse=True):
        if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", upper_text):
            return symbol
    match = re.search(r"\b[A-Z]{2,6}\b", upper_text)
    return match.group(0) if match else None


def _has_any(text: str, words: tuple[str, ...] | list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _clean_plan(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" ，。；;,."))


def _extract_clause(text: str, keywords: tuple[str, ...] | list[str], max_len: int = 34) -> Optional[str]:
    chunks = [chunk.strip() for chunk in re.split(r"[，。；;,.！!？?\n]", text) if chunk.strip()]
    for chunk in chunks:
        if _has_any(chunk, keywords):
            return _clean_plan(chunk[:max_len])
    return None


def _asset_type(asset: str, text: str) -> str:
    upper_asset = asset.upper()
    if upper_asset in STOCK_SYMBOLS or any(word in text for word in ("美股", "股票", "股价")):
        return "stock"
    if re.fullmatch(r"\d{6}", upper_asset):
        return "cn_stock"
    return "crypto"


def _trade_direction(text: str) -> str:
    if _has_any(text, ("观望", "先观察", "等等看", "先不买", "不想追", "watch", "wait")):
        return "watch"
    if any(word in text for word in ("做空", "开空", "空单", "看空", "short", "Short")):
        return "short"
    return "long"


def _intent(text: str) -> str:
    upper_text = text.upper()
    if any(word in upper_text for word in ("KOL", "大V", "博主", "喊单", "老师")):
        return "KOL推荐"
    if "朋友" in text:
        return "朋友推荐"
    if any(word in text for word in ("怕踏空", "怕错过", "错过", "涨太多", "涨很多", "上车", "追高", "已经涨")):
        return "涨很多了怕踏空"
    if any(word in text for word in ("抄底", "补仓", "回本")):
        return "抄底补仓"
    return "自己研究"


def _position_size(text: str) -> Optional[str]:
    def parse_chunk(chunk: str) -> Optional[str]:
        percent = re.search(r"(\d{1,3})\s*%", chunk)
        if percent:
            return f"{percent.group(1)}%"
        fraction = re.search(r"([一二两三四五六七八九十])成仓|([1-9])成仓", chunk)
        if fraction:
            number = fraction.group(1) or fraction.group(2)
            value = NUMBER_WORDS.get(number, int(number) if str(number).isdigit() else 0)
            if value:
                return f"{value * 10}%"
        if any(word in chunk for word in ("ALL IN", "all in", "梭哈", "满仓", "全部")):
            return "ALL IN"
        if "半仓" in chunk:
            return "50%"
        if "重仓" in chunk:
            return "50%"
        if any(word in chunk for word in ("小仓位", "小仓", "轻仓", "试错仓", "小资金", "少量", "一点点")):
            return "5%"
        if any(word in chunk for word in ("中等仓位", "中仓")):
            return "20%"
        return None

    chunks = [chunk.strip() for chunk in re.split(r"[，。；;,.！!？?\n]", text) if chunk.strip()]
    for chunk in chunks:
        if _has_any(chunk, ("仓位", "仓", "投入", "资金", "本金", "准备", "用", "拿", "梭哈", "满仓")):
            parsed = parse_chunk(chunk)
            if parsed:
                return parsed
    match = re.search(r"(\d{1,3})\s*%", text)
    if match and not _has_any(text, ("止盈", "止损", "下跌", "上涨", "反弹", "回撤", "盈利")):
        return f"{match.group(1)}%"
    return None


def _worst_case_plan(text: str, direction: str) -> Optional[str]:
    if direction == "short":
        match = re.search(r"(上涨|涨|反弹|突破)\s*(\d{1,3})\s*%\s*(就)?\s*(止损|平仓|认错|退出)", text)
        if match:
            return f"上涨 {match.group(2)}% 就{match.group(4)}"
        clause = _extract_clause(text, ("上涨", "反弹", "突破", "止损", "平仓", "认错", "退出"))
        if clause:
            return clause
    match = re.search(r"(下跌|跌|回撤|亏损)\s*(\d{1,3})\s*%\s*(就)?\s*(止损|卖出|退出|认错|减仓)", text)
    if match:
        return f"跌 {match.group(2)}% 就{match.group(4)}"
    if _has_any(text, ("跌破关键位置", "跌破支撑", "破位", "跌破计划", "跌破关键位")):
        return _extract_clause(text, ("跌破", "破位")) or "跌破关键位置就退出"
    if _has_any(text, ("止损", "退出", "卖出", "认错", "不对就走", "亏损可控")):
        return _extract_clause(text, ("止损", "退出", "卖出", "认错", "不对就走", "亏损可控")) or "按用户描述止损"
    return None


def _favorable_plan(text: str, direction: str) -> Optional[str]:
    if direction == "short":
        match = re.search(r"(下跌|跌)\s*(\d{1,3})\s*%\s*(就)?\s*(止盈|平仓|减仓|落袋)", text)
        if match:
            return f"下跌 {match.group(2)}% 就{match.group(4)}"
        return _extract_clause(text, ("止盈", "平仓", "减仓", "落袋", "盈利", "赚了", "跌到"))
    match = re.search(r"(上涨|涨|盈利|赚)\s*(\d{1,3})\s*%\s*(就)?\s*(止盈|卖出|减仓|落袋)", text)
    if match:
        return f"上涨 {match.group(2)}% 就{match.group(4)}"
    if _has_any(text, ("止盈", "减仓", "卖一半", "落袋", "移动止损", "涨了不加仓", "盈利后")):
        return _extract_clause(text, ("止盈", "减仓", "卖一半", "落袋", "移动止损", "涨了", "盈利后"))
    return None


def _sideways_plan(text: str) -> Optional[str]:
    match = re.search(r"(横盘|没动静|不涨不跌|震荡)\s*([一二两三四五六七八九十\d]+)\s*(天|周|小时|个月)", text)
    if match:
        return _clean_plan(f"{match.group(1)} {match.group(2)} {match.group(3)}后重新评估")
    if _has_any(text, ("横盘", "没动静", "不涨不跌", "震荡", "等一等", "再观察", "重新评估")):
        return _extract_clause(text, ("横盘", "没动静", "不涨不跌", "震荡", "等一等", "再观察", "重新评估"))
    return None


def _risk_awareness(text: str) -> str:
    if _has_any(text, ("不清楚风险", "不知道风险", "没想过风险", "不太懂风险")):
        return "用户明确表示不清楚风险"
    risk_clauses = []
    for keywords in [
        ("担心追高", "追高"),
        ("估值", "太贵", "泡沫"),
        ("流动性", "滑点", "卖不掉"),
        ("合约", "安全", "蜜罐", "黑名单", "权限"),
        ("业绩", "财报", "增长", "利润"),
        ("政策", "监管"),
        ("波动", "回撤", "亏损"),
    ]:
        clause = _extract_clause(text, keywords)
        if clause and clause not in risk_clauses:
            risk_clauses.append(clause)
    if risk_clauses:
        return "；".join(risk_clauses[:3])
    return "未填写，系统将按风险意识不足处理"


def _horizon(text: str) -> Optional[str]:
    if _has_any(text, ("超短", "日内", "今天", "明天", "马上", "短线", "几天")):
        return "短线"
    if _has_any(text, ("中线", "几周", "一两个月", "1个月", "一个月")):
        return "中线"
    if _has_any(text, ("长期", "长线", "半年", "一年", "几年")):
        return "长线"
    return None


def build_request_from_loose_payload(payload: Any) -> Optional[ImmuneReportRequest]:
    if isinstance(payload, dict) and payload.get("asset") and payload.get("asset_type"):
        data = dict(payload)
        if not data.get("external_market_data"):
            external_market_data = _extract_external_market_data(data)
            if external_market_data:
                data["external_market_data"] = external_market_data
        return ImmuneReportRequest(**data)

    text = _text_from_payload(payload)
    if not text:
        return None
    asset = _extract_asset(text)
    if not asset:
        return None

    direction = _trade_direction(text)
    external_market_data = _extract_external_market_data(payload)
    return ImmuneReportRequest(
        asset=asset,
        asset_type=_asset_type(asset, text),
        trade_direction=direction,
        user_intent=_intent(text),
        user_text=text,
        buy_reason=text,
        risk_awareness=_risk_awareness(text),
        worst_case_plan=_worst_case_plan(text, direction),
        favorable_plan=_favorable_plan(text, direction),
        sideways_plan=_sideways_plan(text),
        position_size=_position_size(text),
        horizon=_horizon(text),
        external_market_data=external_market_data,
    )
