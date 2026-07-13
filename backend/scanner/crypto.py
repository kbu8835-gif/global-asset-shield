from typing import Any, Dict, Optional

import requests

from config import DEXSCREENER_SEARCH_URL, DEXSCREENER_TOKEN_URL, MEME_TOKENS
from scanner.okx_onchain import fetch_okx_onchain_token
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


def _apply_okx_onchain_risk(score: int, reasons: list[str], okx_data: Dict[str, Any]) -> int:
    risk_level_value = okx_data.get("risk_control_level")
    top10_hold = okx_data.get("top10_hold_percent")
    dev_hold = okx_data.get("dev_holding_percent")
    bundle_hold = okx_data.get("bundle_holding_percent")
    suspicious_hold = okx_data.get("suspicious_holding_percent")
    token_tags = okx_data.get("token_tags") or []

    if risk_level_value is not None:
        if risk_level_value >= 4:
            score += 25
            reasons.append("OKX Onchain OS 标记该代币为高风险等级，必须暂停冲动买入")
        elif risk_level_value >= 3:
            score += 15
            reasons.append("OKX Onchain OS 标记该代币为中高风险等级，需要更严格仓位控制")
        elif risk_level_value >= 2:
            score += 5
            reasons.append("OKX Onchain OS 风险等级为中等，不能只看价格涨跌")

    if top10_hold is not None:
        if top10_hold > 40:
            score += 20
            reasons.append(f"OKX 显示 Top 10 持仓占比约 {top10_hold:.2f}%，筹码集中度偏高")
        elif top10_hold > 20:
            score += 10
            reasons.append(f"OKX 显示 Top 10 持仓占比约 {top10_hold:.2f}%，需要关注大户砸盘风险")

    if dev_hold is not None and dev_hold > 5:
        score += 15
        reasons.append(f"OKX 显示开发者持仓约 {dev_hold:.2f}%，需要警惕项目方行为风险")
    if bundle_hold is not None and bundle_hold > 10:
        score += 15
        reasons.append(f"OKX 显示捆绑持仓约 {bundle_hold:.2f}%，疑似集中建仓风险上升")
    if suspicious_hold is not None and suspicious_hold > 5:
        score += 15
        reasons.append(f"OKX 显示可疑地址持仓约 {suspicious_hold:.2f}%，链上资金结构不干净")
    if okx_data.get("is_internal") is True:
        score += 10
        reasons.append("OKX 标记该资产可能存在内盘特征，外部买入者容易处于信息劣势")

    if "honeypot" in token_tags:
        score += 40
        reasons.append("OKX tokenTags 出现 honeypot，可能存在买入后难以卖出的风险")
    if "lowLiquidity" in token_tags:
        score += 20
        reasons.append("OKX tokenTags 出现 lowLiquidity，退出深度不足")

    return score


def scan_crypto(token: str) -> RiskScan:
    score = 20
    reasons = ["Crypto 基础风险分：链上资产波动和流动性风险默认存在"]
    raw_data: Dict[str, Any] = {"input": token}
    okx_data: Optional[Dict[str, Any]] = None

    try:
        okx_data = fetch_okx_onchain_token(token)
    except Exception as exc:
        raw_data["okx_onchain_error"] = exc.__class__.__name__

    if okx_data:
        symbol = okx_data.get("symbol") or token.upper()
        name = okx_data.get("name") or symbol
        token_address = okx_data.get("contract_address") or (token if token.startswith("0x") else None)
        liquidity = float(okx_data.get("liquidity") or 0)
        fdv = float(okx_data.get("market_cap") or 0)
        volume24h = float(okx_data.get("volume24h") or 0)
        raw_data.update(
            {
                "symbol": symbol,
                "name": name,
                "contract_address": token_address,
                "chain": okx_data.get("chain"),
                "dex": "okx_onchainos",
                "price_usd": okx_data.get("price_usd"),
                "fdv": fdv,
                "liquidity": liquidity,
                "volume24h": volume24h,
                "pair_url": None,
                "fallback_mock": False,
                "primary_data_source": "okx_onchainos",
            }
        )
        raw_data["okx_onchain"] = okx_data

        okx_price = okx_data.get("price_usd")
        okx_liquidity = okx_data.get("liquidity")
        okx_market_cap = okx_data.get("market_cap")
        okx_volume = okx_data.get("volume24h")
        okx_holders = okx_data.get("holders")
        okx_liquidity_text = f"${okx_liquidity:,.0f}" if okx_liquidity is not None else "未知"
        reasons.append(
            "OKX Onchain OS 已作为第一数据源读取链上行情："
            f"价格 ${okx_price if okx_price is not None else '未知'}，"
            f"流动性约 {okx_liquidity_text}"
        )
        if okx_market_cap is not None or okx_volume is not None or okx_holders is not None:
            reasons.append(
                f"OKX 链上概览：市值 {('$' + format(okx_market_cap, ',.0f')) if okx_market_cap is not None else '未知'}，"
                f"24h 成交量 {('$' + format(okx_volume, ',.0f')) if okx_volume is not None else '未知'}，"
                f"持有人 {format(okx_holders, ',.0f') if okx_holders is not None else '未知'}"
            )
        score = _apply_okx_onchain_risk(score, reasons, okx_data)
    else:
        try:
            pair = fetch_dexscreener_pair(token)
        except Exception as exc:
            pair = _mock_pair(token)
            reasons.append(f"OKX Onchain OS 暂时不可用，已切换 DexScreener；DexScreener 暂时不可用，已使用 mock fallback：{exc.__class__.__name__}")

        if pair is None:
            pair = _mock_pair(token)
            reasons.append("OKX Onchain OS 暂时不可用，DexScreener 也未找到交易对，已使用 mock fallback，真实交易前必须复核流动性")
        else:
            reasons.append("OKX Onchain OS 暂时不可用，已切换到 DexScreener 作为行情源")

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
                "primary_data_source": "mock" if pair.get("mock") else "dexscreener",
                "okx_onchain": None,
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
