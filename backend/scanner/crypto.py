from typing import Any, Dict, Optional

import requests

from config import DEXSCREENER_SEARCH_URL, DEXSCREENER_TOKEN_URL, MEME_TOKENS
from scanner.utils import clamp_score, risk_level
from schemas import RiskScan


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


def fetch_goplus_security(token: str) -> Optional[Dict[str, Any]]:
    return None


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

    raw_data.update(
        {
            "symbol": symbol,
            "name": name,
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

    if liquidity < 50_000:
        score += 30
        reasons.append("流动性低于 50,000 美元，价格可能被少量资金推拉")
    if fdv > 100_000_000 and liquidity < 500_000:
        score += 25
        reasons.append("FDV 超过 1 亿美元但流动性不足，估值叙事和退出深度不匹配")
    if volume24h < 10_000:
        score += 15
        reasons.append("24 小时成交量低于 10,000 美元，成交质量偏弱")

    security = fetch_goplus_security(token)
    raw_data["goplus_security"] = security
    if security is None:
        score += 10
        reasons.append("没有 GoPlus 安全数据，合约权限、蜜罐和黑名单风险未知")

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
