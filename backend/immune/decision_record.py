from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from database import get_connection, get_demo_user, init_db


@dataclass
class DecisionRecord:
    id: int
    source: str
    user_id: str
    created_at: str
    updated_at: str
    asset: str
    asset_type: str
    trade_direction: str
    user_intent: str
    user_text: str
    buy_reason: str
    position_size: str
    risk_awareness: str
    worst_case_plan: str
    favorable_plan: str
    sideways_plan: str
    risk_score: int
    emotion_score: int
    bias_score: int
    conviction_score: int
    ai_decision: str
    user_decision: str
    summary: str
    status: str
    review_status: str
    notes: str
    mistakes: str
    lesson: str
    next_action: str
    review_result_text: str
    review_outcome_label: str

    @property
    def user_decision_text(self) -> str:
        return " ".join(
            [
                self.asset,
                self.user_intent,
                self.user_text,
                self.buy_reason,
                self.position_size,
                self.risk_awareness,
                self.worst_case_plan,
                self.favorable_plan,
                self.sideways_plan,
                self.notes,
                self.user_decision,
                self.review_result_text,
                self.review_outcome_label,
                self.mistakes,
                self.lesson,
                self.next_action,
            ]
        )

    @property
    def system_decision_text(self) -> str:
        return " ".join([self.summary, self.ai_decision, self.user_decision])

    @property
    def was_reviewed(self) -> bool:
        return self.status == "Reviewed" or self.review_status == "reviewed" or bool(self.mistakes or self.lesson)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _text(row: Dict[str, Any], key: str) -> str:
    return str(row.get(key) or "")


def _status(row: Dict[str, Any]) -> str:
    return _text(row, "status") or ("Reviewed" if row.get("review_status") == "reviewed" else "Open")


def _journal_record(row: Dict[str, Any]) -> DecisionRecord:
    return DecisionRecord(
        id=_safe_int(row.get("id")),
        source="journal_entries",
        user_id=str(row.get("user_id") or ""),
        created_at=_text(row, "created_at"),
        updated_at=_text(row, "updated_at") or _text(row, "created_at"),
        asset=_text(row, "asset"),
        asset_type=_text(row, "asset_type") or "crypto",
        trade_direction=_text(row, "trade_direction") or "long",
        user_intent=_text(row, "user_intent"),
        user_text=_text(row, "user_text"),
        buy_reason=_text(row, "buy_reason"),
        position_size=_text(row, "position_size"),
        risk_awareness=_text(row, "risk_awareness"),
        worst_case_plan=_text(row, "worst_case_plan"),
        favorable_plan=_text(row, "favorable_plan"),
        sideways_plan=_text(row, "sideways_plan"),
        risk_score=_safe_int(row.get("risk_score")),
        emotion_score=_safe_int(row.get("emotion_score")),
        bias_score=_safe_int(row.get("bias_score")),
        conviction_score=_safe_int(row.get("conviction_score")),
        ai_decision=_text(row, "final_decision"),
        user_decision=_text(row, "decision") or _text(row, "final_decision"),
        summary=_text(row, "summary"),
        status=_status(row),
        review_status=_text(row, "review_status"),
        notes=_text(row, "notes"),
        mistakes=_text(row, "mistakes"),
        lesson=_text(row, "lesson"),
        next_action=_text(row, "next_action"),
        review_result_text=_text(row, "review_result_text"),
        review_outcome_label=_text(row, "review_outcome_label"),
    )


def _legacy_record(row: Dict[str, Any]) -> DecisionRecord:
    reason = _text(row, "reason")
    action = _text(row, "action")
    user_decision = _text(row, "user_decision")
    ai_advice = _text(row, "ai_advice")
    return DecisionRecord(
        id=_safe_int(row.get("id")),
        source="investment_journal_entries",
        user_id=_text(row, "user_id"),
        created_at=_text(row, "created_at"),
        updated_at=_text(row, "created_at"),
        asset=_text(row, "asset_symbol"),
        asset_type=_text(row, "asset_type") or "crypto",
        trade_direction="long",
        user_intent=action,
        user_text=reason,
        buy_reason=reason,
        position_size="",
        risk_awareness="",
        worst_case_plan="",
        favorable_plan="",
        sideways_plan="",
        risk_score=_safe_int(row.get("risk_score")),
        emotion_score=100 if _text(row, "emotion_tag").upper() == "FOMO" else 0,
        bias_score=_safe_int(row.get("behavior_risk_score")),
        conviction_score=0,
        ai_decision=ai_advice,
        user_decision=user_decision,
        summary=f"{_text(row, 'asset_symbol')} legacy investment journal: {reason}",
        status="Open",
        review_status="pending",
        notes=reason,
        mistakes="",
        lesson="",
        next_action="",
        review_result_text="",
        review_outcome_label="",
    )


def _numeric_user_id(user_id: int | str) -> Optional[int]:
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def canonical_user_id(user_id: int | str) -> int:
    numeric = _numeric_user_id(user_id)
    if numeric is not None:
        return numeric
    demo = get_demo_user()
    return int(demo["id"])


def list_decision_records(user_id: int | str, limit: int = 50) -> List[DecisionRecord]:
    init_db()
    numeric = _numeric_user_id(user_id)
    records: List[DecisionRecord] = []
    with get_connection() as conn:
        if numeric is not None:
            rows = conn.execute(
                "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (numeric, limit),
            ).fetchall()
            records.extend(_journal_record(dict(row)) for row in rows)
        legacy_rows = conn.execute(
            "SELECT * FROM investment_journal_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (str(user_id), limit),
        ).fetchall()
        records.extend(_legacy_record(dict(row)) for row in legacy_rows)
    records.sort(key=lambda item: item.created_at or "", reverse=True)
    return records[:limit]
