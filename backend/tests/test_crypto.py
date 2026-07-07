from scanner.crypto import scan_crypto


def test_crypto_scanner_external_failure_fallback(monkeypatch):
    def fail(_token):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", fail)
    result = scan_crypto("PEPE")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["fallback_mock"] is True


def test_crypto_scanner_goplus_security_flags(monkeypatch):
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
