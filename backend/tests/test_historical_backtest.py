from scanner.historical import historical_roi


def test_historical_roi_uses_target_price(monkeypatch):
    monkeypatch.setattr("scanner.historical.historical_price", lambda asset, asset_type, target: 12.0)

    roi = historical_roi("TEST", "crypto", 10.0, "2026-06-01T00:00:00+00:00", 7)

    assert roi == 20.0


def test_historical_roi_future_target_returns_none(monkeypatch):
    monkeypatch.setattr("scanner.historical.historical_price", lambda asset, asset_type, target: 12.0)

    roi = historical_roi("TEST", "crypto", 10.0, "2999-06-01T00:00:00+00:00", 7)

    assert roi is None
