from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_connection, init_db
from schemas import (
    InvestmentDNAProfile,
    InvestmentHealthProfile,
    InvestmentJournalCreateRequest,
    InvestmentJournalCreateResponse,
    InvestmentJournalEntry,
    InvestmentOutcomeRequest,
    InvestmentOutcomeResponse,
)


KOL_TERMS = ("KOL", "kol", "朋友推荐", "群里推荐", "老师", "大V", "博主", "喊单")
FOMO_TERMS = ("FOMO", "怕踏空", "追高", "涨很多", "错过", "起飞", "再不上车")
BUY_TERMS = ("buy", "still_buy", "买", "买入", "all in", "梭哈")
AVOID_TERMS = ("don't buy", "dont buy", "不建议", "wait", "观察", "谨慎")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(score: float) -> int:
    return max(0, min(100, round(score)))


def _contains(text: Optional[str], terms: tuple[str, ...]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _opposes_ai(ai_advice: Optional[str], user_decision: Optional[str]) -> bool:
    advice = (ai_advice or "").lower()
    decision = (user_decision or "").lower()
    ai_says_avoid = any(term in advice for term in AVOID_TERMS)
    user_buys = any(term in decision for term in BUY_TERMS)
    ai_says_buy = "buy" in advice or "可以买" in advice or "小仓位" in advice
    user_avoids = "wait" in decision or "don't" in decision or "不买" in decision or "观察" in decision
    return (ai_says_avoid and user_buys) or (ai_says_buy and user_avoids)


def calculate_behavior_risk(
    emotion_tag: Optional[str],
    reason: Optional[str],
    action: Optional[str],
    user_decision: Optional[str],
    ai_advice: Optional[str],
    risk_score: int,
) -> int:
    score = 0
    if _contains(emotion_tag, ("FOMO",)) or _contains(reason, FOMO_TERMS):
        score += 25
    if _contains(reason, KOL_TERMS):
        score += 20
    if _contains(action, ("追涨", "consider_buy after pump", "after pump")):
        score += 20
    if _opposes_ai(ai_advice, user_decision):
        score += 20
    if risk_score > 70:
        score += 15
    return _clamp(score)


def create_investment_journal_entry(payload: InvestmentJournalCreateRequest) -> InvestmentJournalCreateResponse:
    init_db()
    behavior_risk = calculate_behavior_risk(
        payload.emotion_tag,
        payload.reason,
        payload.action,
        payload.user_decision,
        payload.ai_advice,
        payload.risk_score,
    )
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO investment_journal_entries (
                user_id, asset_symbol, asset_type, action, reason, emotion_tag,
                risk_score, behavior_risk_score, ai_advice, user_decision, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.user_id,
                payload.asset_symbol,
                payload.asset_type,
                payload.action,
                payload.reason,
                payload.emotion_tag,
                payload.risk_score,
                behavior_risk,
                payload.ai_advice,
                payload.user_decision,
                _now(),
            ),
        )
        conn.commit()
        entry_id = int(cursor.lastrowid)
    _update_investment_dna(payload.user_id)
    health = _update_investment_health(payload.user_id)
    return InvestmentJournalCreateResponse(
        journal_entry_id=entry_id,
        behavior_risk_score=behavior_risk,
        ai_summary=_build_entry_summary(payload.asset_symbol, behavior_risk, health["health_score"]),
    )


def list_investment_journal_entries(user_id: str) -> List[InvestmentJournalEntry]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM investment_journal_entries WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [InvestmentJournalEntry(**dict(row)) for row in rows]


def submit_investment_outcome(payload: InvestmentOutcomeRequest) -> InvestmentOutcomeResponse:
    init_db()
    with get_connection() as conn:
        entry = conn.execute(
            "SELECT * FROM investment_journal_entries WHERE id = ?",
            (payload.journal_entry_id,),
        ).fetchone()
        if entry is None:
            raise ValueError("Investment journal entry not found")
        conn.execute(
            """
            INSERT INTO investment_outcomes (
                journal_entry_id, outcome_7d, outcome_30d, outcome_90d,
                user_feedback, ai_was_right, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.journal_entry_id,
                payload.outcome_7d,
                payload.outcome_30d,
                payload.outcome_90d,
                payload.user_feedback,
                1 if payload.ai_was_right else 0,
                _now(),
            ),
        )
        conn.commit()
        user_id = str(entry["user_id"])
    dna = _update_investment_dna(user_id)
    health = _update_investment_health(user_id)
    return InvestmentOutcomeResponse(
        updated_dna=InvestmentDNAProfile(**_public_dna(dna)),
        updated_health_score=health["health_score"],
        behavior_summary=_build_outcome_summary(dna, health),
    )


def get_investment_dna(user_id: str) -> InvestmentDNAProfile:
    init_db()
    dna = _ensure_investment_dna(user_id)
    return InvestmentDNAProfile(**_public_dna(dna))


def get_investment_health(user_id: str) -> InvestmentHealthProfile:
    init_db()
    health = _ensure_investment_health(user_id)
    return InvestmentHealthProfile(
        health_score=health["health_score"],
        behavior_risk_score=health["behavior_risk_score"],
        summary=_build_health_summary(user_id, health),
    )


def _update_investment_dna(user_id: str) -> Dict[str, Any]:
    entries = _entries(user_id)
    outcomes = _outcomes_for_user(user_id)
    total = len(entries)
    if total == 0:
        return _ensure_investment_dna(user_id)

    fomo_count = sum(1 for entry in entries if _contains(entry.get("emotion_tag"), ("FOMO",)) or _contains(entry.get("reason"), FOMO_TERMS))
    kol_count = sum(1 for entry in entries if _contains(entry.get("reason"), KOL_TERMS))
    reason_count = sum(1 for entry in entries if (entry.get("reason") or "").strip())
    high_risk_buy_count = sum(
        1
        for entry in entries
        if int(entry.get("risk_score") or 0) > 70 and _contains(entry.get("user_decision"), BUY_TERMS)
    )
    opposed_count = sum(1 for entry in entries if _opposes_ai(entry.get("ai_advice"), entry.get("user_decision")))
    avg_behavior = sum(int(entry.get("behavior_risk_score") or 0) for entry in entries) / total
    avg_risk = sum(int(entry.get("risk_score") or 0) for entry in entries) / total

    dna = {
        "fomo_score": _clamp((fomo_count / total) * 100),
        "discipline_score": _clamp(35 + len(outcomes) * 10 + ((total - opposed_count) / total) * 35),
        "patience_score": _clamp(100 - (fomo_count / total) * 55 - avg_behavior * 0.25),
        "research_score": _clamp((reason_count / total) * 70 + min(len(outcomes) * 6, 30)),
        "risk_control_score": _clamp(100 - (high_risk_buy_count / total) * 55 - avg_risk * 0.2),
        "kol_dependency_score": _clamp((kol_count / total) * 100),
    }
    _save_dna(user_id, dna)
    return _ensure_investment_dna(user_id)


def _update_investment_health(user_id: str) -> Dict[str, Any]:
    dna = _ensure_investment_dna(user_id)
    entries = _entries(user_id)
    avg_behavior = 0 if not entries else sum(int(entry.get("behavior_risk_score") or 0) for entry in entries) / len(entries)
    avoided = sum(
        1
        for entry in entries
        if int(entry.get("risk_score") or 0) > 70
        and _contains(entry.get("ai_advice"), AVOID_TERMS)
        and not _contains(entry.get("user_decision"), BUY_TERMS)
    )
    health_score = _clamp(
        100
        - dna["fomo_score"] * 0.25
        - dna["kol_dependency_score"] * 0.2
        - avg_behavior * 0.25
        + dna["discipline_score"] * 0.15
        + dna["research_score"] * 0.15
    )
    health = {
        "health_score": health_score,
        "behavior_risk_score": _clamp(avg_behavior),
        "monthly_progress": f"本月已记录 {len(entries)} 次投资决策，已避免 {avoided} 次高风险冲动交易。",
        "avoided_risky_trades": avoided,
    }
    _save_health(user_id, health)
    return _ensure_investment_health(user_id)


def _entries(user_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM investment_journal_entries WHERE user_id = ?", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def _outcomes_for_user(user_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT o.*
            FROM investment_outcomes o
            JOIN investment_journal_entries e ON e.id = o.journal_entry_id
            WHERE e.user_id = ?
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _ensure_investment_dna(user_id: str) -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM investment_dna WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO investment_dna (
                    user_id, fomo_score, discipline_score, patience_score, research_score,
                    risk_control_score, kol_dependency_score, updated_at
                )
                VALUES (?, 0, 50, 50, 50, 50, 0, ?)
                """,
                (user_id, _now()),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM investment_dna WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row)


def _ensure_investment_health(user_id: str) -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM investment_health WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO investment_health (
                    user_id, health_score, behavior_risk_score, monthly_progress,
                    avoided_risky_trades, updated_at
                )
                VALUES (?, 50, 0, ?, 0, ?)
                """,
                (user_id, "还没有足够的投资行为记录。先从第一篇投资日记开始。", _now()),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM investment_health WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row)


def _save_dna(user_id: str, dna: Dict[str, int]) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM investment_dna WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE investment_dna
                SET fomo_score = ?, discipline_score = ?, patience_score = ?, research_score = ?,
                    risk_control_score = ?, kol_dependency_score = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    dna["fomo_score"],
                    dna["discipline_score"],
                    dna["patience_score"],
                    dna["research_score"],
                    dna["risk_control_score"],
                    dna["kol_dependency_score"],
                    _now(),
                    user_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO investment_dna (
                    user_id, fomo_score, discipline_score, patience_score, research_score,
                    risk_control_score, kol_dependency_score, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    dna["fomo_score"],
                    dna["discipline_score"],
                    dna["patience_score"],
                    dna["research_score"],
                    dna["risk_control_score"],
                    dna["kol_dependency_score"],
                    _now(),
                ),
            )
        conn.commit()


def _save_health(user_id: str, health: Dict[str, Any]) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM investment_health WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE investment_health
                SET health_score = ?, behavior_risk_score = ?, monthly_progress = ?,
                    avoided_risky_trades = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    health["health_score"],
                    health["behavior_risk_score"],
                    health["monthly_progress"],
                    health["avoided_risky_trades"],
                    _now(),
                    user_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO investment_health (
                    user_id, health_score, behavior_risk_score, monthly_progress,
                    avoided_risky_trades, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    health["health_score"],
                    health["behavior_risk_score"],
                    health["monthly_progress"],
                    health["avoided_risky_trades"],
                    _now(),
                ),
            )
        conn.commit()


def _public_dna(row: Dict[str, Any]) -> Dict[str, int]:
    return {
        "fomo_score": int(row.get("fomo_score") or 0),
        "discipline_score": int(row.get("discipline_score") or 0),
        "patience_score": int(row.get("patience_score") or 0),
        "research_score": int(row.get("research_score") or 0),
        "risk_control_score": int(row.get("risk_control_score") or 0),
        "kol_dependency_score": int(row.get("kol_dependency_score") or 0),
    }


def _build_entry_summary(asset_symbol: str, behavior_risk: int, health_score: int) -> str:
    if behavior_risk >= 75:
        return f"{asset_symbol} 不是唯一风险。你这次的行为风险很高，先停下来写清楚退出条件。当前投资健康值 {health_score}。"
    if behavior_risk >= 45:
        return f"这笔 {asset_symbol} 决策存在明显情绪成分。别急着下单，先把买入逻辑和亏损计划写完整。"
    return f"这笔 {asset_symbol} 决策已记录。继续记录原因和结果，系统会逐步看清你的投资习惯。"


def _build_outcome_summary(dna: Dict[str, Any], health: Dict[str, Any]) -> str:
    return (
        f"复盘已回流。你的 FOMO 分数为 {dna['fomo_score']}，纪律分数为 {dna['discipline_score']}，"
        f"当前投资健康值为 {health['health_score']}。真正的成长来自每一次承认行为模式。"
    )


def _build_health_summary(user_id: str, health: Dict[str, Any]) -> str:
    dna = _ensure_investment_dna(user_id)
    risks = []
    if dna["fomo_score"] >= 60:
        risks.append("高 FOMO")
    if dna["kol_dependency_score"] >= 60:
        risks.append("高 KOL 依赖")
    if dna["discipline_score"] < 50:
        risks.append("低纪律")
    if dna["risk_control_score"] < 50:
        risks.append("风险控制薄弱")
    if not risks:
        return "你的投资行为正在变得更稳定。继续记录每一次决策和结果。"
    return f"你的主要风险不是资产本身，而是{('、').join(risks)}。"
