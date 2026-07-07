from scanner.crypto import scan_crypto
from scanner.cn_stock import scan_cn_stock
from scanner.stock import scan_stock
from schemas import ImmuneReportRequest


def _as_dict(result) -> dict:
    return result if isinstance(result, dict) else result.model_dump()


def run_risk_scan(payload: ImmuneReportRequest) -> dict:
    asset_type = payload.asset_type.lower()
    if asset_type == "crypto":
        return _as_dict(scan_crypto(payload.asset))
    if asset_type == "stock":
        return _as_dict(scan_stock(payload.asset))
    if asset_type == "cn_stock":
        return _as_dict(scan_cn_stock(payload.asset))
    return {
        "risk_score": 70,
        "risk_level": "高风险",
        "risk_reasons": ["未知资产类型，系统无法确认真实风险来源"],
        "raw_data": {"asset": payload.asset, "asset_type": payload.asset_type, "fallback_mock": True},
    }
