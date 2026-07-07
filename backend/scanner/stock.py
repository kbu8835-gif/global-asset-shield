from typing import Any, Dict

import requests
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
    news_items = []
    try:
        news_items = ticker.news or []
    except Exception:
        news_items = []
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
        "revenue_growth": _safe_float(info.get("revenueGrowth")),
        "profit_margin": _safe_float(info.get("profitMargins")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "free_cash_flow": _safe_float(info.get("freeCashflow")),
        "recommendation_key": info.get("recommendationKey"),
        "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
        "news_risk_keywords": _news_risk_keywords(news_items),
        "currency": info.get("currency"),
        "short_name": info.get("shortName") or info.get("longName"),
        "data_source": "yfinance",
        "fallback_mock": False,
    }


def fetch_yahoo_chart_stock(symbol: str) -> Dict[str, Any]:
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}",
        params={"range": "5d", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=12,
    )
    response.raise_for_status()
    result = ((response.json() or {}).get("chart", {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError("Yahoo Chart returned no result")
    meta = result.get("meta") or {}
    quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
    closes = [value for value in quote.get("close", []) if value is not None]
    volumes = [value for value in quote.get("volume", []) if value is not None]
    timestamps = result.get("timestamp") or []
    if not closes:
        raise RuntimeError("Yahoo Chart returned no close prices")

    latest_close = _safe_float(closes[-1] or meta.get("regularMarketPrice"))
    previous_close = _safe_float(closes[-2]) if len(closes) >= 2 else _safe_float(meta.get("previousClose"))
    day_change_percent = None
    if latest_close is not None and previous_close:
        day_change_percent = ((latest_close - previous_close) / previous_close) * 100

    return {
        "symbol": symbol.upper(),
        "price": latest_close,
        "market_cap": None,
        "day_change_percent": day_change_percent,
        "volume": _safe_float(volumes[-1]) if volumes else None,
        "average_volume": None,
        "pe": None,
        "revenue_growth": None,
        "profit_margin": None,
        "debt_to_equity": None,
        "free_cash_flow": None,
        "recommendation_key": None,
        "number_of_analyst_opinions": None,
        "news_risk_keywords": [],
        "currency": meta.get("currency") or "USD",
        "short_name": meta.get("shortName") or f"{symbol.upper()} US Equity",
        "last_trade_time": timestamps[-1] if timestamps else None,
        "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
        "data_source": "yahoo_chart",
        "fallback_mock": False,
        "partial_fallback": True,
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
        "revenue_growth": -0.08 if hot else 0.12,
        "profit_margin": 0.08 if hot else 0.18,
        "debt_to_equity": 180 if hot else 45,
        "free_cash_flow": -500_000_000 if hot else 1_000_000_000,
        "recommendation_key": "hold" if hot else "buy",
        "number_of_analyst_opinions": 18,
        "news_risk_keywords": ["downgrade"] if hot else [],
        "currency": "USD",
        "short_name": f"{symbol.upper()} Mock Equity",
        "data_source": "mock",
        "fallback_mock": True,
    }


def _news_risk_keywords(news_items: list) -> list[str]:
    keywords = ["lawsuit", "fraud", "sec", "investigation", "downgrade", "recall", "bankruptcy", "probe"]
    found: list[str] = []
    for item in news_items[:10]:
        title = str(item.get("title") or item.get("content", {}).get("title") or "").lower()
        summary = str(item.get("summary") or item.get("content", {}).get("summary") or "").lower()
        text = f"{title} {summary}"
        for keyword in keywords:
            if keyword in text and keyword not in found:
                found.append(keyword)
    return found


def scan_stock(symbol: str) -> RiskScan:
    score = 20
    symbol = symbol.strip().upper()
    reasons = ["股票基础风险分：权益资产天然受估值、流动性和市场情绪影响"]

    try:
        raw_data = fetch_us_stock(symbol)
        if raw_data.get("price") is None:
            raise RuntimeError("yfinance returned no price")
    except Exception as exc:
        try:
            raw_data = fetch_yahoo_chart_stock(symbol)
            reasons.append(f"yfinance 暂时不可用，已切换到 Yahoo Chart 免费备用源：{exc.__class__.__name__}")
        except Exception as fallback_exc:
            raw_data = _mock_stock(symbol)
            reasons.append(
                f"yfinance 和 Yahoo Chart 暂时不可用，已使用 mock fallback：{exc.__class__.__name__}/{fallback_exc.__class__.__name__}"
            )

    pe = raw_data.get("pe")
    day_change = raw_data.get("day_change_percent")
    volume = raw_data.get("volume")
    average_volume = raw_data.get("average_volume")
    market_cap = raw_data.get("market_cap")
    revenue_growth = raw_data.get("revenue_growth")
    profit_margin = raw_data.get("profit_margin")
    debt_to_equity = raw_data.get("debt_to_equity")
    free_cash_flow = raw_data.get("free_cash_flow")
    recommendation_key = raw_data.get("recommendation_key")
    news_risk_keywords = raw_data.get("news_risk_keywords") or []

    if not raw_data.get("fallback_mock"):
        price_text = f"${raw_data['price']:,.2f}" if raw_data.get("price") is not None else "未知"
        market_cap_text = f"${market_cap:,.0f}" if market_cap is not None else "未知"
        change_text = f"{day_change:.2f}%" if day_change is not None else "未知"
        data_source = raw_data.get("data_source", "external")
        reasons.append(
            f"{data_source} 已读取 {symbol}：价格 {price_text}，市值 {market_cap_text}，单日涨跌幅 {change_text}，PE {pe if pe is not None else '未知'}"
        )
        if raw_data.get("partial_fallback"):
            reasons.append("Yahoo Chart 备用源提供免费价格和成交量，但不提供完整市值、PE、财报和分析师数据")
        else:
            reasons.append(
                f"基本面快照：营收增长 {revenue_growth if revenue_growth is not None else '未知'}，利润率 {profit_margin if profit_margin is not None else '未知'}，Debt/Equity {debt_to_equity if debt_to_equity is not None else '未知'}"
            )

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
    if revenue_growth is not None and revenue_growth < 0:
        score += 15
        reasons.append("营收增长为负，基本面动能转弱")
    if profit_margin is not None and profit_margin < 0.05:
        score += 10
        reasons.append("利润率低于 5%，盈利安全垫偏薄")
    if debt_to_equity is not None and debt_to_equity > 150:
        score += 15
        reasons.append("Debt/Equity 高于 150，杠杆和利率敏感性偏高")
    if free_cash_flow is not None and free_cash_flow < 0:
        score += 10
        reasons.append("自由现金流为负，增长质量需要复核")
    if recommendation_key in {"sell", "underperform"}:
        score += 10
        reasons.append("分析师共识偏负面，需要复核市场预期")
    if news_risk_keywords:
        score += 15
        reasons.append(f"近期新闻出现风险关键词：{', '.join(news_risk_keywords)}")

    final_score = clamp_score(score)
    return RiskScan(
        risk_score=final_score,
        risk_level=risk_level(final_score),
        risk_reasons=reasons,
        raw_data=raw_data,
    )
