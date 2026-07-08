from fastapi.testclient import TestClient

from auth import get_current_user_or_demo
from app import app
from database import get_connection, init_db
from schemas import UserPublic


def test_get_dna_returns_investment_profile():
    response = TestClient(app).get("/dna")

    assert response.status_code == 200
    data = response.json()
    assert data["investor_type"]
    assert 0 <= data["discipline"] <= 100
    assert 0 <= data["patience"] <= 100
    assert 0 <= data["risk_appetite"] <= 100
    assert 0 <= data["emotion_control"] <= 100
    assert 0 <= data["independent_thinking"] <= 100
    assert data["summary"]


def test_dna_does_not_count_ai_template_kol_mentions_as_user_dependency():
    init_db()
    user_id = 987654
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users (id, email, username, password_hash, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, "dna-no-kol@example.com", "DNA No KOL", "hash", "now", "now"),
        )
        conn.execute("DELETE FROM journal_entries WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM kol_calls WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM kol_profiles WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            INSERT INTO journal_entries (
                created_at, updated_at, title, status, entry_type, user_id,
                asset, asset_type, user_intent, user_text, buy_reason, position_size,
                risk_awareness, worst_case_plan, risk_score, emotion_score, bias_score,
                conviction_score, decision, final_decision, summary, full_report_json, review_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "now", "now", "PEPE", "Open", "immune_report", user_id,
                "PEPE", "crypto", "自己研究", "我自己研究后觉得值得关注",
                "自己研究后关注", "5%", "流动性风险", "跌破计划就退出",
                40, 20, 0, 80, "Wait", "🟡 Wait",
                "AI 模板提醒：不要把 KOL 当作买入理由。",
                '{"munger_lens":{"incentive_check":"KOL 赚的是注意力"}}',
                "pending",
            ),
        )
        conn.commit()

    async def fake_user():
        return UserPublic(id=user_id, email="dna-no-kol@example.com", username="DNA No KOL")

    app.dependency_overrides[get_current_user_or_demo] = fake_user
    try:
        response = TestClient(app).get("/dna")
    finally:
        app.dependency_overrides.pop(get_current_user_or_demo, None)

    assert response.status_code == 200
    data = response.json()
    assert data["kol_dependency"] == 0
    assert "KOL/他人观点相关表达0次" in data["summary"]
    assert "依赖KOL" not in data["summary"]
    assert "外包给了 KOL" not in data["summary"]
