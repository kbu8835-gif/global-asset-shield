from fastapi.testclient import TestClient

from app import app
from scanner.cn_stock import scan_cn_stock


client = TestClient(app)


def test_cn_stock_scanner_external_failure_fallback(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.cn_stock.fetch_cn_stock", fail)
    result = scan_cn_stock("600519")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["symbol"] == "600519"
    assert result.raw_data["fallback_mock"] is True


def test_cn_stock_scan_api_fallback(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.cn_stock.fetch_cn_stock", fail)
    response = client.get("/scan/cn-stock/600519")

    assert response.status_code == 200
    assert response.json()["raw_data"]["fallback_mock"] is True
