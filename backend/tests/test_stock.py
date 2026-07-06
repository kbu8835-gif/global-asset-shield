from scanner.stock import scan_stock


def test_stock_scanner_external_failure_fallback(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.stock.fetch_us_stock", fail)
    result = scan_stock("NVDA")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["fallback_mock"] is True

