from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from scanner.cn_stock import normalize_cn_symbol


def _parse_time(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _closest_price(prices: list, target_ts: float) -> Optional[float]:
    if not prices:
        return None
    closest = min(prices, key=lambda item: abs((item[0] / 1000) - target_ts))
    try:
        return float(closest[1])
    except (TypeError, ValueError, IndexError):
        return None


def _coingecko_id(asset: str, timeout: int = 8) -> Optional[str]:
    response = requests.get("https://api.coingecko.com/api/v3/search", params={"query": asset}, timeout=timeout)
    response.raise_for_status()
    coins = response.json().get("coins") or []
    asset_lower = asset.lower()
    exact = next((coin for coin in coins if str(coin.get("symbol", "")).lower() == asset_lower), None)
    selected = exact or (coins[0] if coins else None)
    return selected.get("id") if selected else None


def crypto_historical_price(asset: str, target: datetime, timeout: int = 8) -> Optional[float]:
    coin_id = _coingecko_id(asset, timeout=timeout)
    if not coin_id:
        return None
    start = int((target - timedelta(days=1)).timestamp())
    end = int((target + timedelta(days=1)).timestamp())
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range",
        params={"vs_currency": "usd", "from": start, "to": end},
        timeout=timeout,
    )
    response.raise_for_status()
    return _closest_price(response.json().get("prices") or [], target.timestamp())


def stock_historical_price(symbol: str, target: datetime) -> Optional[float]:
    import yfinance as yf

    start = (target - timedelta(days=3)).date().isoformat()
    end = (target + timedelta(days=4)).date().isoformat()
    history = yf.Ticker(symbol).history(start=start, end=end)
    if history is None or history.empty:
        return None
    return float(history["Close"].iloc[-1])


def cn_stock_historical_price(symbol: str, target: datetime) -> Optional[float]:
    import akshare as ak

    normalized = normalize_cn_symbol(symbol)
    start = (target - timedelta(days=4)).strftime("%Y%m%d")
    end = (target + timedelta(days=4)).strftime("%Y%m%d")
    history = ak.stock_zh_a_hist(symbol=normalized, period="daily", start_date=start, end_date=end, adjust="")
    if history is None or history.empty:
        return None
    return float(history["收盘"].iloc[-1])


def historical_price(asset: str, asset_type: str, target: datetime) -> Optional[float]:
    try:
        if asset_type == "crypto":
            return crypto_historical_price(asset, target)
        if asset_type == "stock":
            return stock_historical_price(asset, target)
        if asset_type == "cn_stock":
            return cn_stock_historical_price(asset, target)
    except Exception:
        return None
    return None


def historical_roi(asset: str, asset_type: str, call_price: Optional[float], call_time: str | None, days: int) -> Optional[float]:
    if not call_price:
        return None
    parsed = _parse_time(call_time)
    if not parsed:
        return None
    target = parsed + timedelta(days=days)
    if target > datetime.now(timezone.utc):
        return None
    price = historical_price(asset, asset_type, target)
    if price is None:
        return None
    return round(((price - call_price) / call_price) * 100, 4)
