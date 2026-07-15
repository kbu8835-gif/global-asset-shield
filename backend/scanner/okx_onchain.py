import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional

import requests


CHAIN_ID_TO_NAME = {
    "1": "ethereum",
    "501": "solana",
    "56": "bsc",
    "8453": "base",
    "137": "polygon",
    "42161": "arbitrum",
}

OKX_PUBLIC_SPOT_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "XRP": "XRP-USDT",
    "DOGE": "DOGE-USDT",
    "ADA": "ADA-USDT",
    "AVAX": "AVAX-USDT",
    "LINK": "LINK-USDT",
    "BNB": "BNB-USDT",
    "TRX": "TRX-USDT",
    "LTC": "LTC-USDT",
    "BCH": "BCH-USDT",
    "DOT": "DOT-USDT",
    "UNI": "UNI-USDT",
    "OP": "OP-USDT",
    "ARB": "ARB-USDT",
}


class OnchainOSUnavailable(RuntimeError):
    pass


def _run_onchainos(args: List[str], timeout: int = 12) -> Any:
    if not shutil.which("onchainos"):
        raise OnchainOSUnavailable("onchainos command not found")
    result = subprocess.run(
        ["onchainos", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "onchainos failed").strip())
    return _parse_json_output(result.stdout)


def _parse_json_output(output: str) -> Any:
    text = output.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_array = text.find("[")
    first_object = text.find("{")
    starts = [idx for idx in [first_array, first_object] if idx >= 0]
    if not starts:
        raise ValueError("onchainos output is not JSON")
    start = min(starts)
    for end in range(len(text), start, -1):
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            continue
    raise ValueError("onchainos output is not parseable JSON")


def _as_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "items", "tokens", "result", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def fetch_okx_public_ticker(token: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    """Fetch free OKX spot ticker for crypto assets listed on OKX.

    This is intentionally separate from OnchainOS. It does not require a wallet,
    login, or local CLI, so Render can use it as the first source for listed
    assets such as BTC, ETH, SOL, and PEPE.
    """
    symbol = token.strip().upper()
    if not symbol or symbol.startswith("0X") or any(char in symbol for char in "/:_ "):
        return None
    inst_id = OKX_PUBLIC_SPOT_SYMBOLS.get(symbol) or f"{symbol}-USDT"

    response = requests.get(
        "https://www.okx.com/api/v5/market/ticker",
        params={"instId": inst_id},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("code")) != "0":
        return None
    rows = payload.get("data") or []
    if not rows:
        return None
    ticker = rows[0]
    price = _to_float(ticker.get("last"))
    if price is None:
        return None
    volume_ccy = _to_float(ticker.get("volCcy24h"))
    volume_base = _to_float(ticker.get("vol24h"))
    open_24h = _to_float(ticker.get("open24h"))
    price_change_24h = round((price - open_24h) / open_24h * 100, 4) if open_24h else None

    return {
        "source": "okx_public_market",
        "symbol": symbol,
        "name": f"{symbol} OKX Spot",
        "contract_address": None,
        "chain": None,
        "price_usd": price,
        "market_cap": None,
        "liquidity": None,
        "volume24h": volume_ccy if volume_ccy is not None else volume_base,
        "holders": None,
        "pair_url": f"https://www.okx.com/trade-spot/{inst_id.lower()}",
        "primary_data_source": "okx_public_market",
        "is_cex_market_data": True,
        "inst_id": inst_id,
        "price_change_24h": price_change_24h,
        "raw_ticker": ticker,
    }


def _choose_best_token(items: List[Dict[str, Any]], token: str) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    lowered = token.lower()
    exact = [
        item
        for item in items
        if lowered
        in {
            str(item.get("tokenSymbol") or "").lower(),
            str(item.get("tokenContractAddress") or "").lower(),
        }
    ]
    candidates = exact or items
    return max(candidates, key=lambda item: _to_float(item.get("liquidity")) or 0)


def fetch_okx_onchain_token(token: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    query = token.strip()
    if not query:
        return None

    search_payload = _run_onchainos(["token", "search", "--query", query, "--limit", "10"], timeout=timeout)
    token_info = _choose_best_token(_as_list(search_payload), query)
    if not token_info:
        return None

    address = token_info.get("tokenContractAddress")
    if not address:
        return None
    chain = CHAIN_ID_TO_NAME.get(str(token_info.get("chainIndex") or ""), str(token_info.get("chainIndex") or "ethereum"))

    price_info: Dict[str, Any] = {}
    advanced_info: Dict[str, Any] = {}
    liquidity_pools: List[Dict[str, Any]] = []

    try:
        price_payload = _run_onchainos(["token", "price-info", "--address", address, "--chain", chain], timeout=timeout)
        price_items = _as_list(price_payload)
        price_info = price_items[0] if price_items else {}
    except Exception as exc:
        price_info = {"error": exc.__class__.__name__}

    try:
        advanced_payload = _run_onchainos(["token", "advanced-info", "--address", address, "--chain", chain], timeout=timeout)
        advanced_items = _as_list(advanced_payload)
        advanced_info = advanced_items[0] if advanced_items else {}
    except Exception as exc:
        advanced_info = {"error": exc.__class__.__name__}

    try:
        liquidity_payload = _run_onchainos(["token", "liquidity", "--address", address, "--chain", chain], timeout=timeout)
        liquidity_pools = _as_list(liquidity_payload)
    except Exception:
        liquidity_pools = []

    return {
        "source": "okx_onchainos",
        "symbol": token_info.get("tokenSymbol"),
        "name": token_info.get("tokenName"),
        "contract_address": address,
        "chain": chain,
        "community_recognized": ((token_info.get("tagList") or {}).get("communityRecognized")),
        "price_usd": _to_float(price_info.get("price") or token_info.get("price")),
        "market_cap": _to_float(price_info.get("marketCap") or token_info.get("marketCap")),
        "liquidity": _to_float(price_info.get("liquidity") or token_info.get("liquidity")),
        "volume24h": _to_float(price_info.get("volume24H") or token_info.get("volume")),
        "holders": _to_float(price_info.get("holders") or token_info.get("holders")),
        "price_change_1h": _to_float(price_info.get("priceChange1H")),
        "price_change_4h": _to_float(price_info.get("priceChange4H")),
        "price_change_24h": _to_float(price_info.get("priceChange24H") or token_info.get("change")),
        "risk_control_level": _to_float(advanced_info.get("riskControlLevel") or token_info.get("riskLevelControl")),
        "top10_hold_percent": _to_float(advanced_info.get("top10HoldPercent") or token_info.get("top10HoldPercent")),
        "dev_holding_percent": _to_float(advanced_info.get("devHoldingPercent") or token_info.get("devHoldPercent")),
        "bundle_holding_percent": _to_float(advanced_info.get("bundleHoldingPercent") or token_info.get("bundleHoldPercent")),
        "suspicious_holding_percent": _to_float(advanced_info.get("suspiciousHoldingPercent")),
        "sniper_holding_percent": _to_float(advanced_info.get("sniperHoldingPercent")),
        "is_internal": advanced_info.get("isInternal"),
        "token_tags": advanced_info.get("tokenTags") or [],
        "liquidity_pools": liquidity_pools[:5],
        "raw_search": token_info,
        "raw_price_info": price_info,
        "raw_advanced_info": advanced_info,
    }
