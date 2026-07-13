from scanner.stock import scan_stock


def test_stock_scanner_external_failure_fallback(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.stock.fetch_us_stock", fail)
    monkeypatch.setattr("scanner.stock.fetch_yahoo_chart_stock", fail)
    result = scan_stock("NVDA")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["fallback_mock"] is True


def test_stock_scanner_uses_yahoo_chart_before_mock(monkeypatch):
    def fail(_symbol):
        raise RuntimeError("rate limited")

    monkeypatch.setattr("scanner.stock.fetch_us_stock", fail)
    monkeypatch.setattr(
        "scanner.stock.fetch_yahoo_chart_stock",
        lambda symbol: {
            "symbol": symbol.upper(),
            "price": 123.45,
            "market_cap": None,
            "day_change_percent": 1.5,
            "volume": 2_000_000,
            "average_volume": None,
            "pe": None,
            "revenue_growth": None,
            "profit_margin": None,
            "debt_to_equity": None,
            "free_cash_flow": None,
            "recommendation_key": None,
            "news_risk_keywords": [],
            "currency": "USD",
            "short_name": "NVDA US Equity",
            "data_source": "yahoo_chart",
            "fallback_mock": False,
            "partial_fallback": True,
        },
    )

    result = scan_stock("NVDA")

    assert result.raw_data["data_source"] == "yahoo_chart"
    assert result.raw_data["fallback_mock"] is False
    assert any("Yahoo Chart" in reason for reason in result.risk_reasons)


def test_stock_scanner_fundamental_risk(monkeypatch):
    monkeypatch.setattr(
        "scanner.stock.fetch_us_stock",
        lambda _symbol: {
            "symbol": "RISK",
            "price": 10,
            "market_cap": 1_000_000_000,
            "day_change_percent": 1,
            "volume": 1_000_000,
            "average_volume": 1_000_000,
            "pe": 20,
            "revenue_growth": -0.2,
            "profit_margin": 0.02,
            "debt_to_equity": 200,
            "free_cash_flow": -10_000_000,
            "recommendation_key": "sell",
            "news_risk_keywords": ["fraud"],
            "currency": "USD",
            "short_name": "Risk Corp",
            "fallback_mock": False,
        },
    )

    result = scan_stock("RISK")

    assert result.risk_score >= 80
    assert any("营收增长为负" in reason for reason in result.risk_reasons)
    assert any("新闻" in reason for reason in result.risk_reasons)


def test_stock_scanner_accepts_external_okx_market_data(monkeypatch):
    monkeypatch.setattr("scanner.stock.fetch_us_stock", lambda _symbol: (_ for _ in ()).throw(RuntimeError("should not call yfinance")))
    monkeypatch.setattr(
        "scanner.stock.fetch_yahoo_chart_stock",
        lambda _symbol: (_ for _ in ()).throw(RuntimeError("should not call yahoo")),
    )

    result = scan_stock(
        "NVDA",
        external_market_data={
            "source": "OKX Market Agent",
            "symbol": "NVDA",
            "price": 172.5,
            "market_cap": 4_200_000_000_000,
            "day_change_percent": 9.2,
            "volume": 80_000_000,
            "average_volume": 40_000_000,
            "pe": 88,
            "revenue_growth": 0.65,
            "profit_margin": 0.52,
            "debt_to_equity": 35,
            "free_cash_flow": 40_000_000_000,
            "recommendation_key": "buy",
        },
    )

    assert result.raw_data["data_source"] == "okx_market_agent"
    assert result.raw_data["external_market_data_used"] is True
    assert result.raw_data["external_market_data_source"] == "OKX Market Agent"
    assert result.raw_data["price"] == 172.5
    assert result.raw_data["revenue_growth"] == 65
    assert any("OKX Market Agent 美股行情" in reason for reason in result.risk_reasons)
    assert any("PE 高于 80" in reason for reason in result.risk_reasons)
