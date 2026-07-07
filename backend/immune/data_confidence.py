from typing import Any, Dict, List


def _present(value: Any) -> bool:
    if value is None:
        return False
    if value == "":
        return False
    if isinstance(value, (int, float)) and value == 0:
        return False
    return True


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _field_status(raw: Dict[str, Any], mapping: List[tuple[str, str]]) -> tuple[List[str], List[str]]:
    available: List[str] = []
    missing: List[str] = []
    for key, label in mapping:
        if _present(raw.get(key)):
            available.append(label)
        else:
            missing.append(label)
    return available, missing


def build_data_confidence(asset_type: str, risk_scan: Dict[str, Any]) -> Dict[str, Any]:
    raw = risk_scan.get("raw_data") or {}
    asset_type = (asset_type or "").lower()

    if asset_type == "crypto":
        fields = [
            ("price_usd", "实时价格"),
            ("liquidity", "流动性"),
            ("fdv", "FDV/估值"),
            ("volume24h", "24h 成交量"),
            ("pair_url", "交易对链接"),
            ("security_summary", "GoPlus 合约安全"),
        ]
        base_summary = "Crypto 报告依赖交易对流动性、成交量和合约安全数据。"
    elif asset_type == "cn_stock":
        fields = [
            ("price", "实时/近期价格"),
            ("day_change_percent", "涨跌幅"),
            ("volume", "成交量"),
            ("market_cap", "总市值"),
            ("pe", "PE 估值"),
            ("turnover_rate", "换手率"),
        ]
        base_summary = "A股免费源可能只提供轻量行情，基本面字段缺失时不能做完整估值判断。"
    else:
        fields = [
            ("price", "实时/近期价格"),
            ("market_cap", "市值"),
            ("day_change_percent", "单日涨跌幅"),
            ("volume", "成交量"),
            ("pe", "PE 估值"),
            ("revenue_growth", "营收增长"),
            ("profit_margin", "利润率"),
            ("debt_to_equity", "负债水平"),
            ("free_cash_flow", "自由现金流"),
            ("recommendation_key", "分析师共识"),
        ]
        base_summary = "美股报告依赖价格、估值和基本面数据。价格够用不代表研究充分。"

    available, missing = _field_status(raw, fields)
    score = round(len(available) / len(fields) * 100) if fields else 0
    warnings: List[str] = []

    if raw.get("fallback_mock"):
        score -= 45
        warnings.append("当前使用模拟后备数据，不能把这份报告当作真实行情分析。")
    if raw.get("partial_fallback"):
        score -= 10
        warnings.append("主数据源不可用，当前使用备用源。")
    if raw.get("partial_data"):
        score -= 15
        warnings.append("当前数据源只提供轻量行情，部分估值或基本面字段缺失。")
    if asset_type == "crypto" and not raw.get("security_summary"):
        score -= 15
        warnings.append("缺少 GoPlus 合约安全数据，蜜罐、黑名单、owner 权限等风险未知。")

    score = _clamp(score)
    if score >= 75:
        level = "High Confidence"
        decision_gate = "数据相对充分，可以继续结合行为风险判断。"
    elif score >= 50:
        level = "Medium Confidence"
        decision_gate = "数据只够做初步判断，不适合重仓决策。"
    elif score >= 25:
        level = "Low Confidence"
        decision_gate = "数据不足，最终决策至少应该降级为 Wait。"
    else:
        level = "Very Low Confidence"
        decision_gate = "数据严重不足，不建议基于当前报告买入。"

    if missing:
        summary = f"{base_summary} 当前缺少：{', '.join(missing[:5])}。"
    else:
        summary = f"{base_summary} 本次关键字段基本齐全。"
    if warnings:
        summary += " " + warnings[0]

    return {
        "score": score,
        "level": level,
        "available": available,
        "missing": missing,
        "warnings": warnings,
        "decision_gate": decision_gate,
        "summary": summary,
    }
