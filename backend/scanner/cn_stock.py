from typing import Any, Dict

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
        "fallback_mock": True,
    }


def fetch_cn_stock(symbol: str) -> Dict[str, Any]:
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
        "fallback_mock": False,
    }


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
        reasons.append(
            f"akshare 已读取 {raw_data.get('name') or normalized}：价格 {price_text}，总市值 {market_cap_text}，涨跌幅 {change_text}，PE {pe if pe is not None else '未知'}"
        )

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
