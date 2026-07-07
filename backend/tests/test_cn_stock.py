from fastapi.testclient import TestClient

from app import app
from scanner.cn_stock import fetch_cn_stock, scan_cn_stock


client = TestClient(app)


def test_cn_stock_uses_eastmoney_first(monkeypatch):
    def eastmoney(_symbol):
        return {
            "symbol": "600519",
            "name": "贵州茅台",
            "price": 1500.0,
            "day_change_percent": 1.2,
            "volume": 100000,
            "turnover_rate": 0.5,
            "pe": 28,
            "market_cap": 1_800_000_000_000,
            "is_st": False,
            "currency": "CNY",
            "data_source": "eastmoney",
            "fallback_mock": False,
        }

    monkeypatch.setattr("scanner.cn_stock.fetch_eastmoney_cn_stock", eastmoney)
    result = fetch_cn_stock("600519")

    assert result["data_source"] == "eastmoney"
    assert result["price"] == 1500.0


def test_cn_stock_falls_back_to_sina_after_eastmoney_failure(monkeypatch):
    def eastmoney_fail(_symbol):
        raise RuntimeError("eastmoney down")

    def sina(_symbol):
        return {
            "symbol": "600519",
            "name": "贵州茅台",
            "price": 1495.0,
            "day_change_percent": 0.8,
            "volume": 95000,
            "turnover_rate": None,
            "pe": None,
            "market_cap": None,
            "is_st": False,
            "currency": "CNY",
            "data_source": "sina",
            "fallback_mock": False,
            "partial_data": True,
        }

    monkeypatch.setattr("scanner.cn_stock.fetch_eastmoney_cn_stock", eastmoney_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_sina_cn_stock", sina)
    result = fetch_cn_stock("600519")

    assert result["data_source"] == "sina"
    assert result["partial_fallback"] is True
    assert result["fallback_reason"] == "eastmoney:RuntimeError"


def test_cn_stock_falls_back_to_yahoo_after_china_sources_fail(monkeypatch):
    def eastmoney_fail(_symbol):
        raise RuntimeError("eastmoney down")

    def sina_fail(_symbol):
        raise RuntimeError("sina down")

    def yahoo(_symbol):
        return {
            "symbol": "600519",
            "name": "Kweichow Moutai",
            "price": 1488.0,
            "day_change_percent": -0.8,
            "volume": 85000,
            "turnover_rate": None,
            "pe": None,
            "market_cap": None,
            "is_st": False,
            "currency": "CNY",
            "data_source": "yahoo_cn_chart",
            "fallback_mock": False,
            "partial_data": True,
        }

    monkeypatch.setattr("scanner.cn_stock.fetch_eastmoney_cn_stock", eastmoney_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_sina_cn_stock", sina_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_yahoo_cn_stock", yahoo)
    result = fetch_cn_stock("600519")

    assert result["data_source"] == "yahoo_cn_chart"
    assert result["partial_fallback"] is True
    assert result["fallback_reason"] == "eastmoney:RuntimeError;sina:RuntimeError"


def test_cn_stock_falls_back_to_akshare_after_light_sources_fail(monkeypatch):
    def eastmoney_fail(_symbol):
        raise RuntimeError("eastmoney down")

    def sina_fail(_symbol):
        raise RuntimeError("sina down")

    def yahoo_fail(_symbol):
        raise RuntimeError("yahoo down")

    def akshare(_symbol):
        return {
            "symbol": "600519",
            "name": "贵州茅台",
            "price": 1490.0,
            "day_change_percent": -0.5,
            "volume": 90000,
            "turnover_rate": 0.4,
            "pe": 27,
            "market_cap": 1_780_000_000_000,
            "is_st": False,
            "currency": "CNY",
            "data_source": "akshare",
            "fallback_mock": False,
        }

    monkeypatch.setattr("scanner.cn_stock.fetch_eastmoney_cn_stock", eastmoney_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_sina_cn_stock", sina_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_yahoo_cn_stock", yahoo_fail)
    monkeypatch.setattr("scanner.cn_stock.fetch_akshare_cn_stock", akshare)
    result = fetch_cn_stock("600519")

    assert result["data_source"] == "akshare"
    assert result["partial_fallback"] is True
    assert result["fallback_reason"] == "eastmoney:RuntimeError;sina:RuntimeError;yahoo:RuntimeError"


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


def test_stock_scan_api_auto_detects_cn_stock(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.cn_stock.fetch_cn_stock", fail)
    response = client.get("/scan/stock/600519")

    assert response.status_code == 200
    data = response.json()
    assert data["raw_data"]["symbol"] == "600519"
    assert data["raw_data"]["currency"] == "CNY"
    assert any("A股" in reason for reason in data["risk_reasons"])
