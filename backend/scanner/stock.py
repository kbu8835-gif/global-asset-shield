from typing import Any, Dict

import yfinance as yf

from config import HOT_STOCKS
from scanner.utils import clamp_score, risk_level
from schemas import RiskScan


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_us_stock(symbol: str) -> Dict[str, Any]:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    history = ticker.history(period="5d")
    latest_close = None
    previous_close = info.get("previousClose")
    day_change_percent = None
    latest_volume = info.get("volume")

    if history is not None and not history.empty:
        latest_close = _safe_float(history["Close"].iloc[-1])
        latest_volume = _safe_float(history["Volume"].iloc[-1])
        if len(history) >= 2:
            previous_close = previous_close or _safe_float(history["Close"].iloc[-2])
        if latest_close and previous_close:
            day_change_percent = ((latest_close - float(previous_close)) / float(previous_close)) * 100

    return {
        "symbol": symbol.upper(),
        "price": latest_close or _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "market_cap": _safe_float(info.get("marketCap")),
        "day_change_percent": day_change_percent,
        "volume": _safe_float(latest_volume),
        "average_volume": _safe_float(info.get("averageVolume") or info.get("averageDailyVolume10Day")),
        "pe": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
        "currency": info.get("currency"),
        "short_name": info.get("shortName") or info.get("longName"),
        "fallback_mock": False,
    }


def _mock_stock(symbol: str) -> Dict[str, Any]:
    hot = symbol.upper() in HOT_STOCKS
    return {
        "symbol": symbol.upper(),
        "price": 100.0,
        "market_cap": 900_000_000_000 if hot else 20_000_000_000,
        "day_change_percent": 9.5 if hot else 1.2,
        "volume": None if hot else 2_000_000,
        "average_volume": 1_000_000,
        "pe": 95 if hot else 25,
        "currency": "USD",
        "short_name": f"{symbol.upper()} Mock Equity",
        "fallback_mock": True,
    }


def scan_stock(symbol: str) -> RiskScan:
    score = 20
    symbol = symbol.strip().upper()
    reasons = ["股票基础风险分：权益资产天然受估值、流动性和市场情绪影响"]

    try:
        raw_data = fetch_us_stock(symbol)
    except Exception as exc:
        raw_data = _mock_stock(symbol)
        reasons.append(f"yfinance 暂时不可用，已使用 mock fallback：{exc.__class__.__name__}")

    pe = raw_data.get("pe")
    day_change = raw_data.get("day_change_percent")
    volume = raw_data.get("volume")
    average_volume = raw_data.get("average_volume")
    market_cap = raw_data.get("market_cap")

    if pe is not None and pe > 80:
        score += 20
        reasons.append("PE 高于 80，价格对增长预期非常敏感")
    if day_change is not None and abs(day_change) > 8:
        score += 20
        reasons.append("单日涨跌幅超过 8%，短线情绪和波动风险偏高")
    if volume is None or (average_volume and volume > average_volume * 2):
        score += 15
        reasons.append("成交量缺失或明显异常，当前价格可能受事件和情绪驱动")
    if market_cap is None:
        score += 10
        reasons.append("市值数据缺失，基础估值判断不完整")
    if symbol in HOT_STOCKS:
        score += 10
        reasons.append("属于热门高波动股票，容易吸引追涨和叙事交易")

    final_score = clamp_score(score)
    return RiskScan(
        risk_score=final_score,
        risk_level=risk_level(final_score),
        risk_reasons=reasons,
        raw_data=raw_data,
    )

