from scanner.crypto import scan_crypto


def test_crypto_scanner_external_failure_fallback(monkeypatch):
    def fail(_token):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: None)
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", fail)
    result = scan_crypto("PEPE")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["fallback_mock"] is True


def test_crypto_scanner_goplus_security_flags(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: None)
    monkeypatch.setattr(
        "scanner.crypto.fetch_dexscreener_pair",
        lambda _token: {
            "baseToken": {"symbol": "TEST", "name": "Test Token", "address": "0xabc"},
            "chainId": "ethereum",
            "dexId": "uniswap",
            "priceUsd": "1",
            "fdv": 10_000_000,
            "liquidity": {"usd": 1_000_000},
            "volume": {"h24": 100_000},
            "url": "https://dexscreener.com/test",
        },
    )
    monkeypatch.setattr(
        "scanner.crypto.fetch_goplus_security",
        lambda _token, _chain=None: {
            "is_honeypot": "1",
            "is_blacklisted": "1",
            "is_mintable": "1",
            "is_proxy": "1",
            "buy_tax": "0.12",
            "sell_tax": "0.15",
            "is_open_source": "0",
        },
    )

    result = scan_crypto("0xabc")

    assert result.risk_score >= 80
    assert result.raw_data["security_summary"]["is_honeypot"] is True
    assert any("蜜罐" in reason for reason in result.risk_reasons)


def test_crypto_scanner_okx_onchain_enrichment(monkeypatch):
    monkeypatch.setattr(
        "scanner.crypto.fetch_dexscreener_pair",
        lambda _token: {
            "baseToken": {"symbol": "PEPE", "name": "Pepe", "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933"},
            "chainId": "ethereum",
            "dexId": "uniswap",
            "priceUsd": "0.0000027",
            "fdv": 1_100_000_000,
            "liquidity": {"usd": 20_000_000},
            "volume": {"h24": 740_000},
            "url": "https://dexscreener.com/ethereum/pepe",
        },
    )
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)
    monkeypatch.setattr(
        "scanner.crypto.fetch_okx_onchain_token",
        lambda _token: {
            "source": "okx_onchainos",
            "price_usd": 0.000002741,
            "market_cap": 1_130_000_000,
            "liquidity": 20_490_000,
            "volume24h": 740_190,
            "holders": 568_148,
            "risk_control_level": 2,
            "top10_hold_percent": 8.0739,
            "dev_holding_percent": 0,
            "bundle_holding_percent": 0,
            "token_tags": [],
        },
    )

    result = scan_crypto("PEPE")

    assert result.raw_data["okx_onchain"]["source"] == "okx_onchainos"
    assert result.raw_data["primary_data_source"] == "okx_onchainos"
    assert result.raw_data["okx_onchain"]["holders"] == 568_148
    assert any("OKX Onchain OS" in reason for reason in result.risk_reasons)


def test_crypto_scanner_uses_external_okx_agent_data(monkeypatch):
    monkeypatch.setattr("scanner.crypto.fetch_okx_onchain_token", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call cli")))
    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", lambda _token: (_ for _ in ()).throw(RuntimeError("should not call dexscreener")))
    monkeypatch.setattr("scanner.crypto.fetch_goplus_security", lambda _token, _chain=None: None)

    result = scan_crypto(
        "PEPE",
        external_market_data={
            "source": "OKX Onchain OS Agent",
            "symbol": "PEPE",
            "price": 0.000002741,
            "market_cap": 1_130_000_000,
            "liquidity": 20_490_000,
            "volume24h": 740_190,
            "holders": 568_148,
            "risk_control_level": 2,
            "top10_hold_percent": 8.0739,
        },
    )

    assert result.raw_data["primary_data_source"] == "external_okx_agent"
    assert result.raw_data["external_market_data_used"] is True
    assert result.raw_data["okx_onchain"]["holders"] == 568_148
    assert any("调用方 Agent 传入的 OKX 链上行情" in reason for reason in result.risk_reasons)
