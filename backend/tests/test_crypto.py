from scanner.crypto import scan_crypto


def test_crypto_scanner_external_failure_fallback(monkeypatch):
    def fail(_token):
        raise RuntimeError("network down")

    monkeypatch.setattr("scanner.crypto.fetch_dexscreener_pair", fail)
    result = scan_crypto("PEPE")

    assert result.risk_score > 0
    assert result.risk_level in {"低风险", "中风险", "高风险", "极高风险"}
    assert result.raw_data["fallback_mock"] is True

