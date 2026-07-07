import time

from immune.llm import build_ai_coach, fallback_ai_coach
from schemas import ImmuneReportRequest


def _payload():
    return ImmuneReportRequest(
        asset="PEPE",
        asset_type="crypto",
        user_intent="KOL推荐",
        user_text="这个币涨了很多，我怕踏空，准备梭哈",
        buy_reason="看到KOL推荐",
        risk_awareness="不清楚风险",
        worst_case_plan="跌了就再看看",
        position_size="50%",
        horizon="短线",
    )


def _report():
    return {
        "asset": "PEPE",
        "asset_type": "crypto",
        "risk_scan": {"risk_score": 75, "risk_reasons": ["mock"]},
        "emotion_scan": {"emotion_score": 90, "detected_emotions": ["FOMO"]},
        "bias_detection": {"bias_score": 80, "biases": [{"bias_type": "FOMO"}]},
        "conviction_score": {"score": 20},
        "final_decision": "🔴 Don't Buy",
        "position_advice": "不建议买入",
        "kol_risk_scan": {"kol_detected": True},
        "munger_lens": {"munger_verdict": "No"},
    }


def test_llm_fallback_has_coach_message():
    result = fallback_ai_coach(_payload(), _report())

    assert "coach_message" in result
    assert "behavior_pattern" in result
    assert "next_action" in result


def test_deepseek_quota_limits_calls(monkeypatch):
    user_id = int(time.time_ns() % 1_000_000_000)
    monkeypatch.setattr("immune.llm.LLM_ENABLED", True)
    monkeypatch.setattr("immune.llm.DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("immune.llm.LLM_DAILY_LIMIT", 1)
    monkeypatch.setattr(
        "immune.llm._call_deepseek",
        lambda _payload, _report: {
            "coach_message": "先停手。",
            "behavior_pattern": "你在追逐别人的叙事。",
            "next_action": "等待 24 小时。",
        },
    )

    first = build_ai_coach(_payload(), _report(), user_id)
    second = build_ai_coach(_payload(), _report(), user_id)

    assert first["source"] == "deepseek"
    assert first["remaining"] == 0
    assert second["source"] == "limit_exceeded"
    assert second["fallback_used"] is True
