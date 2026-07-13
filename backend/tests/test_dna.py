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


def test_dna_returns_evidence_sources_from_user_records():
    init_db()
    user_id = 987655
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users (id, email, username, password_hash, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, "dna-evidence@example.com", "DNA Evidence", "hash", "now", "now"),
        )
        conn.execute("DELETE FROM journal_entries WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            INSERT INTO journal_entries (
                created_at, updated_at, title, status, entry_type, user_id,
                asset, asset_type, user_intent, user_text, buy_reason, position_size,
                risk_awareness, worst_case_plan, risk_score, emotion_score, bias_score,
                conviction_score, decision, final_decision, summary, full_report_json, review_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-07-13T10:00:00", "2026-07-13T10:00:00", "PEPE Evidence", "Open", "immune_report", user_id,
                "PEPE", "crypto", "自己研究", "最近涨很多，我怕踏空",
                "自己研究但担心错过", "50%", "不清楚风险", "跌了就再看看",
                82, 75, 60, 25, "Wait", "🔴 Don't Buy",
                "高风险，不建议买入。", "{}", "pending", "看到价格起飞以后才开始关注",
            ),
        )
        conn.commit()

    async def fake_user():
        return UserPublic(id=user_id, email="dna-evidence@example.com", username="DNA Evidence")

    app.dependency_overrides[get_current_user_or_demo] = fake_user
    try:
        response = TestClient(app).get("/dna")
    finally:
        app.dependency_overrides.pop(get_current_user_or_demo, None)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_window"] == "最近1条"
    assert data["evidence_sources"]
    fomo = next(group for group in data["evidence_sources"] if group["signal"] == "FOMO / 追涨")
    assert fomo["count"] == 1
    assert fomo["records"][0]["asset"] == "PEPE"
    assert fomo["records"][0]["keyword"] in ["涨很多", "怕踏空", "起飞"]
    assert "系统模板里的 KOL 提醒不会被计入" in next(
        group for group in data["evidence_sources"] if group["signal"] == "KOL / 外部观点"
    )["explanation"]


def test_dna_includes_review_feedback_after_notebook_review():
    create_response = TestClient(app).post(
        "/notebook",
        json={
            "asset": "ETH",
            "asset_type": "crypto",
            "title": "ETH review evidence",
            "decision": "Wait",
            "notes": "自己研究后关注",
            "buy_reason": "等待突破",
            "risk_awareness": "波动风险",
            "worst_case_plan": "跌破计划就退出",
            "position_size": "5%",
        },
    )
    assert create_response.status_code == 200
    notebook_id = create_response.json()["id"]

    review_response = TestClient(app).post(
        f"/notebook/{notebook_id}/review",
        json={"current_price": 0, "user_result_text": "结果下跌后我没有止损，一直死扛。"},
    )
    assert review_response.status_code == 200

    dna_response = TestClient(app).get("/dna")
    assert dna_response.status_code == 200
    review_group = next(group for group in dna_response.json()["evidence_sources"] if group["signal"] == "复盘结果回流")
    assert review_group["count"] >= 1
    assert any(record["record_id"] == notebook_id and "死扛" in record["excerpt"] for record in review_group["records"])

    TestClient(app).delete(f"/notebook/{notebook_id}")
