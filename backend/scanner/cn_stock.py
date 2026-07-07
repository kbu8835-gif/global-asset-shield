from typing import Any, Dict

import requests

from scanner.utils import clamp_score, risk_level
from schemas import RiskScan


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def normalize_cn_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace(".SH", "").replace(".SZ", "").replace("SH", "").replace("SZ", "")
    return cleaned.zfill(6) if cleaned.isdigit() and len(cleaned) <= 6 else cleaned


def _eastmoney_secid(symbol: str) -> str:
    normalized = normalize_cn_symbol(symbol)
    market = "1" if normalized.startswith(("5", "6", "9")) else "0"
    return f"{market}.{normalized}"


def _sina_symbol(symbol: str) -> str:
    normalized = normalize_cn_symbol(symbol)
    prefix = "sh" if normalized.startswith(("5", "6", "9")) else "sz"
    return f"{prefix}{normalized}"


def _yahoo_symbol(symbol: str) -> str:
    normalized = normalize_cn_symbol(symbol)
    suffix = "SS" if normalized.startswith(("5", "6", "9")) else "SZ"
    return f"{normalized}.{suffix}"


def _eastmoney_scaled(value: Any, scale: float = 100) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    return number / scale


def _mock_cn_stock(symbol: str) -> Dict[str, Any]:
    normalized = normalize_cn_symbol(symbol)
    hot = normalized in {"600519", "300750", "000001", "000858", "002594"}
    return {
        "symbol": normalized,
        "name": "贵州茅台 Mock" if normalized == "600519" else f"{normalized} Mock A Share",
        "price": 1680.0 if normalized == "600519" else 25.0,
        "day_change_percent": 8.9 if hot else 1.6,
        "volume": 3_500_000 if hot else 900_000,
        "turnover_rate": 6.8 if hot else 1.2,
        "pe": 42 if normalized == "600519" else 88 if hot else 28,
        "market_cap": 2_100_000_000_000 if normalized == "600519" else 35_000_000_000,
        "is_st": normalized.startswith("ST") or normalized.endswith("ST"),
        "currency": "CNY",
        "data_source": "mock",
        "fallback_mock": True,
    }


def fetch_eastmoney_cn_stock(symbol: str) -> Dict[str, Any]:
    normalized = normalize_cn_symbol(symbol)
    response = requests.get(
        "https://push2.eastmoney.com/api/qt/stock/get",
        params={
            "secid": _eastmoney_secid(normalized),
            "fields": "f43,f57,f58,f47,f116,f162,f168,f169,f170",
        },
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
        timeout=12,
    )
    response.raise_for_status()
    data = (response.json() or {}).get("data") or {}
    if not data or data.get("f43") in (None, "-"):
        raise ValueError("Eastmoney returned no price")
    name = data.get("f58") or normalized
    return {
        "symbol": normalized,
        "name": name,
        "price": _eastmoney_scaled(data.get("f43")),
        "day_change_percent": _eastmoney_scaled(data.get("f170")),
        "volume": _safe_float(data.get("f47")),
        "turnover_rate": _eastmoney_scaled(data.get("f168")),
        "pe": _eastmoney_scaled(data.get("f162")),
        "market_cap": _safe_float(data.get("f116")),
        "is_st": "ST" in str(name).upper(),
        "currency": "CNY",
        "data_source": "eastmoney",
        "fallback_mock": False,
    }


def fetch_akshare_cn_stock(symbol: str) -> Dict[str, Any]:
    import akshare as ak

    normalized = normalize_cn_symbol(symbol)
    spot = ak.stock_zh_a_spot_em()
    row = spot[spot["代码"].astype(str) == normalized]
    if row.empty:
        raise ValueError("A-share symbol not found")
    item = row.iloc[0].to_dict()
    return {
        "symbol": normalized,
        "name": item.get("名称"),
        "price": _safe_float(item.get("最新价")),
        "day_change_percent": _safe_float(item.get("涨跌幅")),
        "volume": _safe_float(item.get("成交量")),
        "turnover_rate": _safe_float(item.get("换手率")),
        "pe": _safe_float(item.get("市盈率-动态") or item.get("市盈率")),
        "market_cap": _safe_float(item.get("总市值")),
        "is_st": "ST" in str(item.get("名称") or "").upper(),
        "currency": "CNY",
        "data_source": "akshare",
        "fallback_mock": False,
    }


def fetch_sina_cn_stock(symbol: str) -> Dict[str, Any]:
    normalized = normalize_cn_symbol(symbol)
    response = requests.get(
        f"https://hq.sinajs.cn/list={_sina_symbol(normalized)}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"},
        timeout=12,
    )
    response.raise_for_status()
    response.encoding = "gbk"
    text = response.text
    if '="' not in text:
        raise ValueError("Sina returned malformed quote")
    payload = text.split('="', 1)[1].split('";', 1)[0]
    fields = payload.split(",")
    if len(fields) < 32 or not fields[0]:
        raise ValueError("Sina returned no quote fields")
    name = fields[0]
    open_price = _safe_float(fields[1])
    previous_close = _safe_float(fields[2])
    price = _safe_float(fields[3])
    volume = _safe_float(fields[8])
    day_change_percent = None
    if price is not None and previous_close:
        day_change_percent = ((price - previous_close) / previous_close) * 100
    if price is None or price <= 0:
        raise ValueError("Sina returned no live price")
    return {
        "symbol": normalized,
        "name": name,
        "price": price,
        "open_price": open_price,
        "previous_close": previous_close,
        "day_change_percent": day_change_percent,
        "volume": volume,
        "turnover_rate": None,
        "pe": None,
        "market_cap": None,
        "is_st": "ST" in str(name).upper(),
        "currency": "CNY",
        "data_source": "sina",
        "fallback_mock": False,
        "partial_data": True,
    }


def fetch_yahoo_cn_stock(symbol: str) -> Dict[str, Any]:
    normalized = normalize_cn_symbol(symbol)
    yahoo_symbol = _yahoo_symbol(normalized)
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
        params={"range": "5d", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=12,
    )
    response.raise_for_status()
    result = ((response.json() or {}).get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError("Yahoo returned no chart")
    meta = result.get("meta") or {}
    quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
    closes = [value for value in quote.get("close", []) if value is not None]
    volumes = [value for value in quote.get("volume", []) if value is not None]
    if not closes:
        raise ValueError("Yahoo returned no close prices")
    price = _safe_float(closes[-1] or meta.get("regularMarketPrice"))
    previous_close = _safe_float(closes[-2]) if len(closes) >= 2 else _safe_float(meta.get("previousClose"))
    day_change_percent = None
    if price is not None and previous_close:
        day_change_percent = ((price - previous_close) / previous_close) * 100
    return {
        "symbol": normalized,
        "name": meta.get("shortName") or yahoo_symbol,
        "price": price,
        "previous_close": previous_close,
        "day_change_percent": day_change_percent,
        "volume": _safe_float(volumes[-1]) if volumes else None,
        "turnover_rate": None,
        "pe": None,
        "market_cap": None,
        "is_st": "ST" in str(meta.get("shortName") or "").upper(),
        "currency": meta.get("currency") or "CNY",
        "data_source": "yahoo_cn_chart",
        "fallback_mock": False,
        "partial_data": True,
    }


def fetch_cn_stock(symbol: str) -> Dict[str, Any]:
    try:
        return fetch_eastmoney_cn_stock(symbol)
    except Exception as eastmoney_exc:
        try:
            data = fetch_sina_cn_stock(symbol)
            data["partial_fallback"] = True
            data["fallback_reason"] = f"eastmoney:{eastmoney_exc.__class__.__name__}"
            return data
        except Exception as sina_exc:
            try:
                data = fetch_yahoo_cn_stock(symbol)
                data["partial_fallback"] = True
                data["fallback_reason"] = f"eastmoney:{eastmoney_exc.__class__.__name__};sina:{sina_exc.__class__.__name__}"
                return data
            except Exception as yahoo_exc:
                data = fetch_akshare_cn_stock(symbol)
                data["partial_fallback"] = True
                data["fallback_reason"] = (
                    f"eastmoney:{eastmoney_exc.__class__.__name__};"
                    f"sina:{sina_exc.__class__.__name__};"
                    f"yahoo:{yahoo_exc.__class__.__name__}"
                )
                return data


def scan_cn_stock(symbol: str) -> RiskScan:
    score = 20
    normalized = normalize_cn_symbol(symbol)
    reasons = ["A股基础风险分：权益资产受估值、题材情绪、流动性和政策预期共同影响"]

    try:
        raw_data = fetch_cn_stock(normalized)
    except Exception as exc:
        raw_data = _mock_cn_stock(normalized)
        reasons.append(f"A股行情源暂时不可用，已使用 mock fallback：{exc.__class__.__name__}")

    pe = raw_data.get("pe")
    day_change = raw_data.get("day_change_percent")
    turnover_rate = raw_data.get("turnover_rate")
    market_cap = raw_data.get("market_cap")
    is_st = bool(raw_data.get("is_st"))

    if not raw_data.get("fallback_mock"):
        price_text = f"¥{raw_data['price']:,.2f}" if raw_data.get("price") is not None else "未知"
        market_cap_text = f"¥{market_cap:,.0f}" if market_cap is not None else "未知"
        change_text = f"{day_change:.2f}%" if day_change is not None else "未知"
        data_source = raw_data.get("data_source", "A股行情源")
        reasons.append(
            f"{data_source} 已读取 {raw_data.get('name') or normalized}：价格 {price_text}，总市值 {market_cap_text}，涨跌幅 {change_text}，PE {pe if pe is not None else '未知'}"
        )
        if raw_data.get("partial_fallback"):
            reasons.append(f"主行情源暂时不可用，已切换到 {data_source} 备用源：{raw_data.get('fallback_reason')}")
        if raw_data.get("partial_data"):
            reasons.append("当前备用源只提供价格、涨跌幅和成交量，PE、市值、换手率等基础面字段暂时缺失")

    if is_st:
        score += 30
        reasons.append("名称包含 ST，存在退市、经营或财务异常风险")
    if pe is not None and pe > 80:
        score += 20
        reasons.append("PE 高于 80，估值对增长预期和情绪非常敏感")
    if day_change is not None and day_change >= 8:
        score += 20
        reasons.append("单日涨幅接近涨停，追高和题材情绪风险明显")
    if turnover_rate is not None and turnover_rate > 10:
        score += 15
        reasons.append("换手率高于 10%，短线资金博弈和筹码松动风险偏高")
    if market_cap is not None and market_cap < 5_000_000_000:
        score += 15
        reasons.append("总市值低于 50 亿，小盘股波动和流动性风险更高")
    if market_cap is None:
        score += 10
        reasons.append("市值数据缺失，基础估值判断不完整")

    final_score = clamp_score(score)
    return RiskScan(
        risk_score=final_score,
        risk_level=risk_level(final_score),
        risk_reasons=reasons,
        raw_data=raw_data,
    )
