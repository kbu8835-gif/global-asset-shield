from typing import Any, Dict, Optional

import requests

from config import DEXSCREENER_SEARCH_URL, DEXSCREENER_TOKEN_URL, MEME_TOKENS
from scanner.okx_onchain import fetch_okx_onchain_token, fetch_okx_public_ticker
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


def _normalized_tax(data: Dict[str, Any], *keys: str) -> float:
    return round(_tax(_first_value(data, *keys)), 4)


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


def _first_value(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _to_float(value: Any, default: float = 0) -> float:
    try:
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("$", "").replace("`", "").strip()
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
            return float(cleaned) * multiplier
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_external_market_data(token: str, external_market_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not external_market_data:
        return None
    data = dict(external_market_data)
    source = str(data.get("source") or data.get("data_source") or data.get("provider") or data.get("数据源") or "external_market_data")
    source_lower = source.lower()
    primary_source = "external_okx_agent" if "okx" in source_lower or "onchain" in source_lower else "external_market_data"

    risk_value = _first_value(data, "risk_control_level", "riskLevelControl", "risk_level", "riskLevel", "risk", "风险控制等级")
    top10_value = _first_value(
        data,
        "top10_hold_percent",
        "top10HoldPercent",
        "top10HolderPercent",
        "top_10_holders_percent",
        "top10HolderRatio",
        "top10_holding_ratio",
        "Top10 持仓占比",
        "top10持仓占比",
    )
    dev_value = _first_value(data, "dev_holding_percent", "devHoldingPercent", "developer_holding_percent", "devHoldPercent")
    bundle_value = _first_value(data, "bundle_holding_percent", "bundleHoldingPercent", "bundleHoldPercent")
    suspicious_value = _first_value(data, "suspicious_holding_percent", "suspiciousHoldingPercent", "suspiciousHoldPercent")
    holders_value = _first_value(data, "holders", "holder_count", "holderCount", "holdersCount", "holder", "持有人", "持有人数")
    liquidity_change_value = _first_value(
        data,
        "liquidity_change_24h",
        "liquidityChange24h",
        "liquidity_change_percent_24h",
        "liquidityChangePercent24h",
    )
    pool_depth_value = _first_value(data, "pool_depth_usd", "poolDepthUsd", "pool_depth", "depth_usd", "depthUsd")
    pair_url = _first_value(
        data,
        "pair_url",
        "pairUrl",
        "pool_url",
        "poolUrl",
        "okx_url",
        "okxUrl",
        "token_url",
        "tokenUrl",
        "explorer_url",
        "explorerUrl",
        "交易池链接",
        "交易对链接",
        "链接",
    )
    owner_privilege = str(_first_value(data, "owner_privilege", "ownerPrivilege", "owner_risk", "ownerRisk") or "").lower()
    token_tags = data.get("token_tags") or data.get("tokenTags") or []
    token_tags = [str(tag).lower() for tag in token_tags] if isinstance(token_tags, list) else [str(token_tags).lower()]
    security_summary = {
        "is_honeypot": _flag(_first_value(data, "is_honeypot", "honeypot", "isHoneypot")),
        "is_blacklisted": _flag(_first_value(data, "is_blacklisted", "blacklist", "isBlacklisted")),
        "is_mintable": _flag(_first_value(data, "is_mintable", "mintable", "can_mint", "isMintable")),
        "is_proxy": _flag(_first_value(data, "is_proxy", "proxy", "isProxy")),
        "can_take_back_ownership": _flag(
            _first_value(data, "can_take_back_ownership", "canTakeBackOwnership", "can_take_ownership")
        )
        or owner_privilege in {"high", "strong", "danger", "dangerous"},
        "owner_change_balance": _flag(_first_value(data, "owner_change_balance", "ownerChangeBalance", "can_change_balance")),
        "buy_tax_percent": _normalized_tax(data, "buy_tax", "buyTax", "buy_tax_percent", "buyTaxPercent"),
        "sell_tax_percent": _normalized_tax(data, "sell_tax", "sellTax", "sell_tax_percent", "sellTaxPercent"),
        "is_open_source": not _flag(_first_value(data, "not_open_source", "is_closed_source", "closedSource")),
        "owner_privilege": owner_privilege or None,
        "source": source,
    }
    has_security_fields = any(
        key in data
        for key in [
            "is_honeypot",
            "honeypot",
            "isHoneypot",
            "is_blacklisted",
            "blacklist",
            "isBlacklisted",
            "is_mintable",
            "isMintable",
            "is_proxy",
            "isProxy",
            "owner_privilege",
            "ownerPrivilege",
            "buy_tax",
            "buyTax",
            "sell_tax",
            "sellTax",
        ]
    )

    return {
        "source": source,
        "symbol": _first_value(data, "symbol", "token_symbol", "tokenSymbol", "币种", "代币", "资产") or token.upper(),
        "name": _first_value(data, "name", "token_name", "tokenName", "名称") or token.upper(),
        "contract_address": _first_value(data, "contract_address", "address", "token_address", "contractAddress", "合约", "合约地址")
        or (token if token.startswith("0x") else None),
        "chain": _first_value(data, "chain", "chain_id", "chainId", "network", "链", "网络"),
        "price_usd": _to_float(
            _first_value(data, "price_usd", "priceUsd", "price", "lastPrice", "last", "markPrice", "价格")
        ),
        "market_cap": _to_float(_first_value(data, "market_cap", "marketCap", "fdv", "mcap", "marketValue", "市值", "估值")),
        "liquidity": _to_float(_first_value(data, "liquidity", "liquidity_usd", "liquidityUsd", "liquidityUSD", "流动性")),
        "volume24h": _to_float(
            _first_value(data, "volume24h", "volume_24h", "volume24H", "volume24hUsd", "volumeUsd24h", "volume", "h24_volume", "24h成交量", "24小时成交量", "成交量")
        ),
        "pair_url": pair_url,
        "holders": _to_float(holders_value) if holders_value is not None else None,
        "risk_control_level": _to_float(risk_value, -1) if risk_value is not None else None,
        "top10_hold_percent": _to_float(top10_value) if top10_value is not None else None,
        "dev_holding_percent": _to_float(dev_value) if dev_value is not None else None,
        "bundle_holding_percent": _to_float(bundle_value) if bundle_value is not None else None,
        "suspicious_holding_percent": _to_float(suspicious_value) if suspicious_value is not None else None,
        "is_internal": data.get("is_internal") if "is_internal" in data else data.get("isInternal"),
        "token_tags": token_tags,
        "security_summary": security_summary if has_security_fields else None,
        "liquidity_change_24h": _to_float(liquidity_change_value) if liquidity_change_value is not None else None,
        "pool_depth_usd": _to_float(pool_depth_value) if pool_depth_value is not None else None,
        "pool_depth_warning": _flag(_first_value(data, "pool_depth_warning", "poolDepthWarning", "depth_warning")),
        "liquidity_locked": _flag(_first_value(data, "liquidity_locked", "liquidityLocked")),
        "liquidity_lock_percent": _to_float(_first_value(data, "liquidity_lock_percent", "liquidityLockPercent")),
        "raw_external_market_data": data,
        "primary_data_source": primary_source,
    }


def _apply_okx_onchain_risk(score: int, reasons: list[str], okx_data: Dict[str, Any]) -> int:
    risk_level_value = okx_data.get("risk_control_level")
    top10_hold = okx_data.get("top10_hold_percent")
    dev_hold = okx_data.get("dev_holding_percent")
    bundle_hold = okx_data.get("bundle_holding_percent")
    suspicious_hold = okx_data.get("suspicious_holding_percent")
    token_tags = okx_data.get("token_tags") or []
    security = okx_data.get("security_summary") or {}
    liquidity_change_24h = okx_data.get("liquidity_change_24h")
    pool_depth_usd = okx_data.get("pool_depth_usd")

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

    if security.get("is_honeypot") or "honeypot" in token_tags:
        score += 40
        reasons.append("OKX 安全数据标记疑似蜜罐，可能存在买入后难以卖出的风险")
    if security.get("is_blacklisted"):
        score += 30
        reasons.append("OKX 安全数据提示黑名单风险，地址可能被限制交易")
    if security.get("is_mintable"):
        score += 15
        reasons.append("OKX 安全数据提示合约可能存在增发权限，持有人可能被稀释")
    if security.get("is_proxy"):
        score += 10
        reasons.append("OKX 安全数据提示代理合约风险，合约逻辑可能被升级改变")
    if security.get("can_take_back_ownership") or security.get("owner_change_balance"):
        score += 15
        reasons.append("OKX 安全数据提示 owner 权限较强，可能影响持有人余额或合约控制权")
    if security.get("buy_tax_percent", 0) > 10 or security.get("sell_tax_percent", 0) > 10:
        score += 15
        reasons.append(
            f"OKX 安全数据提示买卖税偏高：买税 {security.get('buy_tax_percent', 0)}%，卖税 {security.get('sell_tax_percent', 0)}%"
        )
    if "lowliquidity" in token_tags or "low_liquidity" in token_tags:
        score += 20
        reasons.append("OKX tokenTags 出现 lowLiquidity，退出深度不足")
    if liquidity_change_24h is not None and liquidity_change_24h < -25:
        score += 15
        reasons.append(f"OKX 显示 24h 流动性下降约 {abs(liquidity_change_24h):.2f}%，需要警惕撤池或深度变薄")
    if okx_data.get("pool_depth_warning") or (pool_depth_usd is not None and pool_depth_usd < 50_000):
        score += 15
        reasons.append("OKX 池子深度提示不足，较小资金也可能造成明显滑点")

    return score


def scan_crypto(token: str, external_market_data: Optional[Dict[str, Any]] = None) -> RiskScan:
    score = 20
    reasons = ["Crypto 基础风险分：链上资产波动和流动性风险默认存在"]
    raw_data: Dict[str, Any] = {"input": token}
    okx_data: Optional[Dict[str, Any]] = _normalize_external_market_data(token, external_market_data)

    if okx_data:
        raw_data["external_market_data_used"] = True
        raw_data["external_market_data_source"] = okx_data.get("source")
    else:
        try:
            okx_data = fetch_okx_public_ticker(token)
        except Exception as exc:
            raw_data["okx_public_market_error"] = exc.__class__.__name__
        if not okx_data:
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
                "pair_url": okx_data.get("pair_url"),
                "fallback_mock": False,
                "primary_data_source": okx_data.get("primary_data_source") or "okx_onchainos",
                "is_cex_market_data": bool(okx_data.get("is_cex_market_data")),
                "inst_id": okx_data.get("inst_id"),
            }
        )
        raw_data["okx_onchain"] = okx_data
        raw_data["okx_security_summary"] = okx_data.get("security_summary")
        raw_data["liquidity_change_24h"] = okx_data.get("liquidity_change_24h")
        raw_data["pool_depth_usd"] = okx_data.get("pool_depth_usd")
        raw_data["pool_depth_warning"] = okx_data.get("pool_depth_warning")

        okx_price = okx_data.get("price_usd")
        okx_liquidity = okx_data.get("liquidity")
        okx_market_cap = okx_data.get("market_cap")
        okx_volume = okx_data.get("volume24h")
        okx_holders = okx_data.get("holders")
        is_cex_market_data = bool(okx_data.get("is_cex_market_data"))
        okx_liquidity_text = f"${okx_liquidity:,.0f}" if okx_liquidity is not None else "不适用"
        if raw_data.get("external_market_data_used"):
            reasons.append(
                "已使用调用方 Agent 传入的 OKX 链上行情作为第一数据源："
                f"价格 ${okx_price if okx_price is not None else '未知'}，"
                f"流动性约 {okx_liquidity_text}"
            )
        elif is_cex_market_data:
            reasons.append(
                "已直接使用 OKX 公共现货行情作为第一数据源："
                f"{okx_data.get('inst_id') or symbol} 价格 ${okx_price if okx_price is not None else '未知'}，"
                f"24h 成交量 {('$' + format(okx_volume, ',.0f')) if okx_volume is not None else '未知'}"
            )
        else:
            reasons.append(
                "OKX Onchain OS 已作为第一数据源读取链上行情："
                f"价格 ${okx_price if okx_price is not None else '未知'}，"
                f"流动性约 {okx_liquidity_text}"
            )
        if okx_market_cap is not None or okx_volume is not None or okx_holders is not None:
            if is_cex_market_data:
                reasons.append(
                    "OKX 公共行情用于解决主流币价格准确性；链上持仓、蜜罐和 owner 权限不适用于 BTC 这类现货报价。"
                )
            else:
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

    is_cex_market_data = bool(raw_data.get("is_cex_market_data"))

    if not is_cex_market_data and liquidity < 50_000:
        score += 30
        reasons.append("流动性低于 50,000 美元，价格可能被少量资金推拉")
    if not is_cex_market_data and fdv > 100_000_000 and liquidity < 500_000:
        score += 25
        reasons.append("FDV 超过 1 亿美元但流动性不足，估值叙事和退出深度不匹配")
    if volume24h < 10_000:
        score += 15
        reasons.append("24 小时成交量低于 10,000 美元，成交质量偏弱")

    external_security_summary = raw_data.get("okx_security_summary") if raw_data.get("external_market_data_used") else None
    if is_cex_market_data:
        security = None
        security_summary = None
        raw_data["security_source"] = "not_applicable_for_okx_spot"
    elif external_security_summary:
        security = None
        security_summary = external_security_summary
        raw_data["security_source"] = "OKX Onchain OS Agent"
    else:
        chain_for_security = raw_data.get("chain")
        try:
            security = fetch_goplus_security(token_address or token, chain_for_security)
        except Exception as exc:
            security = None
            raw_data["goplus_error"] = exc.__class__.__name__
        security_summary = _security_summary(security) if security else None
    raw_data["goplus_security"] = security
    raw_data["security_summary"] = security_summary
    if is_cex_market_data:
        reasons.append("OKX 现货行情不按合约代币处理，GoPlus 蜜罐/owner 权限扫描不适用")
    elif external_security_summary:
        reasons.append("已使用调用方 Agent 传入的 OKX 合约安全数据")
    elif security is None:
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
