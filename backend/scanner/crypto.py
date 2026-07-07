from typing import Any, Dict, Optional

import requests

from config import DEXSCREENER_SEARCH_URL, DEXSCREENER_TOKEN_URL, MEME_TOKENS
from scanner.utils import clamp_score, risk_level
from schemas import RiskScan

GOPLUS_CHAIN_IDS = {
    "ethereum": "1",
    "eth": "1",
    "bsc": "56",
    "binance-smart-chain": "56",
    "polygon": "137",
    "arbitrum": "42161",
    "optimism": "10",
    "base": "8453",
    "avalanche": "43114",
    "fantom": "250",
}


def fetch_dexscreener_pair(token: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
    token = token.strip()
    if not token:
        return None

    if token.startswith("0x") and len(token) >= 20:
        response = requests.get(f"{DEXSCREENER_TOKEN_URL}/{token}", timeout=timeout)
    else:
        response = requests.get(DEXSCREENER_SEARCH_URL, params={"q": token}, timeout=timeout)

    response.raise_for_status()
    pairs = response.json().get("pairs") or []
    if not pairs:
        return None
    return max(pairs, key=lambda pair: (pair.get("liquidity") or {}).get("usd") or 0)


def fetch_goplus_security(token: str, chain: str | None = None, timeout: int = 8) -> Optional[Dict[str, Any]]:
    address = token.strip()
    if not address.startswith("0x"):
        return None
    chain_id = GOPLUS_CHAIN_IDS.get((chain or "ethereum").lower(), chain or "1")
    response = requests.get(
        f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
        params={"contract_addresses": address},
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json().get("result") or {}
    return result.get(address.lower()) or result.get(address)


def _flag(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def _tax(value: Any) -> float:
    try:
        return float(value or 0) * (100 if float(value or 0) <= 1 else 1)
    except (TypeError, ValueError):
        return 0


def _security_summary(security: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "is_honeypot": _flag(security.get("is_honeypot")),
        "is_blacklisted": _flag(security.get("is_blacklisted")),
        "is_mintable": _flag(security.get("is_mintable")),
        "is_proxy": _flag(security.get("is_proxy")),
        "can_take_back_ownership": _flag(security.get("can_take_back_ownership")),
        "owner_change_balance": _flag(security.get("owner_change_balance")),
        "buy_tax_percent": round(_tax(security.get("buy_tax")), 4),
        "sell_tax_percent": round(_tax(security.get("sell_tax")), 4),
        "is_open_source": _flag(security.get("is_open_source")),
    }


def _mock_pair(token: str) -> Dict[str, Any]:
    lowered = token.lower()
    is_meme = any(word in lowered for word in MEME_TOKENS)
    return {
        "mock": True,
        "baseToken": {"symbol": token.upper(), "name": f"{token.upper()} Mock Token"},
        "chainId": "mock-chain",
        "dexId": "mock-dex",
        "priceUsd": "0.00001" if is_meme else "1.0",
        "fdv": 150_000_000 if is_meme else 20_000_000,
        "liquidity": {"usd": 35_000 if is_meme else 250_000},
        "volume": {"h24": 8_000 if is_meme else 80_000},
        "url": "https://dexscreener.com",
    }


def scan_crypto(token: str) -> RiskScan:
    score = 20
    reasons = ["Crypto 基础风险分：链上资产波动和流动性风险默认存在"]
    raw_data: Dict[str, Any] = {"input": token}

    try:
        pair = fetch_dexscreener_pair(token)
    except Exception as exc:
        pair = _mock_pair(token)
        reasons.append(f"DexScreener 暂时不可用，已使用 mock fallback：{exc.__class__.__name__}")

    if pair is None:
        pair = _mock_pair(token)
        reasons.append("DexScreener 未找到交易对，已使用 mock fallback，真实交易前必须复核流动性")

    liquidity = float((pair.get("liquidity") or {}).get("usd") or 0)
    fdv = float(pair.get("fdv") or pair.get("marketCap") or 0)
    volume24h = float((pair.get("volume") or {}).get("h24") or 0)
    base_token = pair.get("baseToken") or {}
    symbol = base_token.get("symbol") or token.upper()
    name = base_token.get("name") or symbol
    token_address = base_token.get("address") or (token if token.startswith("0x") else None)

    raw_data.update(
        {
            "symbol": symbol,
            "name": name,
            "contract_address": token_address,
            "chain": pair.get("chainId"),
            "dex": pair.get("dexId"),
            "price_usd": pair.get("priceUsd"),
            "fdv": fdv,
            "liquidity": liquidity,
            "volume24h": volume24h,
            "pair_url": pair.get("url"),
            "fallback_mock": bool(pair.get("mock")),
        }
    )

    if not pair.get("mock"):
        reasons.append(
            f"DexScreener 已读取 {symbol}：价格 ${raw_data['price_usd']}，流动性约 ${liquidity:,.0f}，FDV 约 ${fdv:,.0f}，24h 成交量约 ${volume24h:,.0f}"
        )

    if liquidity < 50_000:
        score += 30
        reasons.append("流动性低于 50,000 美元，价格可能被少量资金推拉")
    if fdv > 100_000_000 and liquidity < 500_000:
        score += 25
        reasons.append("FDV 超过 1 亿美元但流动性不足，估值叙事和退出深度不匹配")
    if volume24h < 10_000:
        score += 15
        reasons.append("24 小时成交量低于 10,000 美元，成交质量偏弱")

    try:
        security = fetch_goplus_security(token_address or token, pair.get("chainId"))
    except Exception as exc:
        security = None
        raw_data["goplus_error"] = exc.__class__.__name__
    security_summary = _security_summary(security) if security else None
    raw_data["goplus_security"] = security
    raw_data["security_summary"] = security_summary
    if security is None:
        score += 10
        reasons.append("没有 GoPlus 安全数据，合约权限、蜜罐和黑名单风险未知")
    else:
        reasons.append("GoPlus 已读取合约安全数据")
        if security_summary["is_honeypot"]:
            score += 40
            reasons.append("GoPlus 标记疑似蜜罐，买入后可能无法正常卖出")
        if security_summary["is_blacklisted"]:
            score += 30
            reasons.append("GoPlus 标记存在黑名单风险")
        if security_summary["is_mintable"]:
            score += 15
            reasons.append("合约存在增发权限，持有人可能被稀释")
        if security_summary["is_proxy"]:
            score += 10
            reasons.append("合约为代理合约，逻辑可能被升级改变")
        if security_summary["can_take_back_ownership"] or security_summary["owner_change_balance"]:
            score += 15
            reasons.append("Owner 权限较强，存在取回所有权或改变余额风险")
        if security_summary["buy_tax_percent"] > 10 or security_summary["sell_tax_percent"] > 10:
            score += 15
            reasons.append("买卖税超过 10%，进出成本和滑点风险偏高")
        if not security_summary["is_open_source"]:
            score += 10
            reasons.append("合约未开源，外部审查难度更高")

    haystack = f"{token} {symbol} {name}".lower()
    if any(word in haystack for word in MEME_TOKENS):
        score += 10
        reasons.append("输入或名称包含 meme 高波动资产信号")

    final_score = clamp_score(score)
    return RiskScan(
        risk_score=final_score,
        risk_level=risk_level(final_score),
        risk_reasons=reasons,
        raw_data=raw_data,
    )
