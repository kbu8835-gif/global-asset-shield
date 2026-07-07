import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_connection, init_db
from immune.coach import build_ai_coach
from immune.direction import normalize_trade_direction
from schemas import (
    NotebookCreate,
    NotebookDetail,
    NotebookListItem,
    NotebookReviewRequest,
    NotebookUpdate,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> Dict[str, Any]:
    return dict(row) if row else {}


def _status(row: Dict[str, Any]) -> str:
    return row.get("status") or ("Reviewed" if row.get("review_status") == "reviewed" else "Open")


def _decision(row: Dict[str, Any]) -> str:
    return row.get("decision") or row.get("final_decision") or "Wait"


def _title(row: Dict[str, Any]) -> str:
    return row.get("title") or row.get("asset") or "Untitled"


def _updated_at(row: Dict[str, Any]) -> str:
    return row.get("updated_at") or row.get("created_at") or _now()


def _analysis(row: Dict[str, Any]) -> Dict[str, Any]:
    try:
        report = json.loads(row.get("full_report_json") or "{}")
    except json.JSONDecodeError:
        report = {}
    return {
        "risk": {
            "score": row.get("risk_score") or 0,
            "detail": report.get("risk_scan", {}),
        },
        "emotion": {
            "score": row.get("emotion_score") or 0,
            "detail": report.get("emotion_scan", {}),
        },
        "bias": {
            "score": row.get("bias_score") or 0,
            "detail": report.get("bias_detection", {}),
        },
        "conviction": {
            "score": row.get("conviction_score") or 0,
            "detail": report.get("conviction_score", {}),
        },
    }


def _report_json(row: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(row.get("full_report_json") or "{}")
    except json.JSONDecodeError:
        return {}


def _trade_direction(row: Dict[str, Any]) -> str:
    report = _report_json(row)
    return normalize_trade_direction(row.get("trade_direction") or report.get("trade_direction") or "long")


def _timeline(row: Dict[str, Any]) -> List[Dict[str, str]]:
    events = [{"date": row.get("created_at") or "", "event": "Created"}]
    if row.get("full_report_json"):
        events.append({"date": row.get("created_at") or "", "event": "Immune Report"})
    if row.get("updated_at") and row.get("updated_at") != row.get("created_at"):
        events.append({"date": row.get("updated_at") or "", "event": "User Edited"})
    if row.get("review_status") == "reviewed" or row.get("lesson") or row.get("mistakes"):
        events.append({"date": row.get("review_date") or row.get("updated_at") or "", "event": "Review"})
    if _status(row) == "Archived":
        events.append({"date": row.get("updated_at") or "", "event": "Archived"})
    return events


def _detail(row: Dict[str, Any]) -> NotebookDetail:
    return NotebookDetail(
        id=row["id"],
        title=_title(row),
        asset=row.get("asset") or "",
        asset_type=row.get("asset_type") or "crypto",
        trade_direction=_trade_direction(row),
        decision=_decision(row),
        status=_status(row),
        entry_type=row.get("entry_type") or "immune_report",
        created_at=row.get("created_at") or "",
        updated_at=_updated_at(row),
        review_date=row.get("review_date"),
        user_intent=row.get("user_intent"),
        user_text=row.get("user_text"),
        buy_reason=row.get("buy_reason"),
        risk_awareness=row.get("risk_awareness"),
        worst_case_plan=row.get("worst_case_plan"),
        position_size=row.get("position_size"),
        notes=row.get("notes"),
        mistakes=row.get("mistakes"),
        lesson=row.get("lesson"),
        next_action=row.get("next_action"),
        ai_analysis=_analysis(row),
        ai_coach=build_ai_coach(row),
        timeline=_timeline(row),
    )


def list_notebooks(user_id: int) -> List[NotebookListItem]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
            (user_id,),
        ).fetchall()
    items = []
    for row in rows:
        data = _row_to_dict(row)
        items.append(
            NotebookListItem(
                id=data["id"],
                title=_title(data),
                asset=data.get("asset") or "",
                asset_type=data.get("asset_type") or "crypto",
                trade_direction=_trade_direction(data),
                decision=_decision(data),
                status=_status(data),
                entry_type=data.get("entry_type") or "immune_report",
                created_at=data.get("created_at") or "",
                updated_at=_updated_at(data),
                review_date=data.get("review_date"),
            )
        )
    return items


def get_notebook(notebook_id: int, user_id: int) -> Optional[NotebookDetail]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ? AND user_id = ?", (notebook_id, user_id)).fetchone()
    return _detail(_row_to_dict(row)) if row else None


def create_notebook(payload: NotebookCreate, user_id: int) -> NotebookDetail:
    init_db()
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO journal_entries (
                created_at, updated_at, title, status, entry_type,
                user_id,
                asset, asset_type, trade_direction, user_text, buy_reason, risk_awareness, worst_case_plan,
                position_size, risk_score, emotion_score, bias_score, conviction_score,
                decision, final_decision, summary, full_report_json, review_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                payload.title or payload.asset,
                payload.status or "Open",
                payload.entry_type or "manual",
                user_id,
                payload.asset,
                payload.asset_type,
                normalize_trade_direction(payload.trade_direction),
                payload.notes or "",
                payload.buy_reason or "",
                payload.risk_awareness or "",
                payload.worst_case_plan or "",
                payload.position_size or "",
                0,
                0,
                0,
                0,
                payload.decision or "Wait",
                payload.decision or "Wait",
                "Manual notebook entry",
                json.dumps({"trade_direction": normalize_trade_direction(payload.trade_direction)}, ensure_ascii=False),
                "pending",
                payload.notes or "",
            ),
        )
        conn.commit()
        notebook_id = int(cursor.lastrowid)
    created = get_notebook(notebook_id, user_id)
    if created is None:
        raise RuntimeError("failed to create notebook")
    return created


def update_notebook(notebook_id: int, payload: NotebookUpdate, user_id: int) -> Optional[NotebookDetail]:
    init_db()
    allowed = {
        "asset",
        "asset_type",
        "title",
        "decision",
        "status",
        "entry_type",
        "notes",
        "buy_reason",
        "user_text",
        "risk_awareness",
        "worst_case_plan",
        "position_size",
        "mistakes",
        "lesson",
        "next_action",
        "review_date",
        "trade_direction",
    }
    updates = {key: value for key, value in payload.model_dump(exclude_unset=True).items() if key in allowed}
    trade_direction_update = updates.pop("trade_direction", None)
    updates["updated_at"] = _now()
    if "decision" in updates:
        updates["final_decision"] = updates["decision"]
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM journal_entries WHERE id = ? AND user_id = ?", (notebook_id, user_id)).fetchone()
        if row is None:
            return None
        if trade_direction_update is not None:
            current_row = conn.execute("SELECT full_report_json FROM journal_entries WHERE id = ? AND user_id = ?", (notebook_id, user_id)).fetchone()
            report = _report_json(_row_to_dict(current_row))
            normalized_direction = normalize_trade_direction(trade_direction_update)
            updates["trade_direction"] = normalized_direction
            report["trade_direction"] = normalized_direction
            updates["full_report_json"] = json.dumps(report, ensure_ascii=False)
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        conn.execute(f"UPDATE journal_entries SET {set_clause} WHERE id = ? AND user_id = ?", list(updates.values()) + [notebook_id, user_id])
        conn.commit()
    return get_notebook(notebook_id, user_id)


def delete_notebook(notebook_id: int, user_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM journal_entries WHERE id = ? AND user_id = ?", (notebook_id, user_id)).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM journal_entries WHERE id = ? AND user_id = ?", (notebook_id, user_id))
        conn.commit()
    return True


def review_notebook(notebook_id: int, payload: NotebookReviewRequest, user_id: int) -> Optional[NotebookDetail]:
    current = get_notebook(notebook_id, user_id)
    if current is None:
        return None
    text = payload.user_result_text
    mistake = "逻辑正确但市场波动"
    if any(word in text + (current.user_text or "") for word in ["怕踏空", "追高", "涨很多", "起飞"]):
        mistake = "FOMO 追高"
    elif any(word in text + (current.buy_reason or "") for word in ["KOL", "大V", "喊单"]):
        mistake = "KOL 盲从"
    elif any(word in text + (current.position_size or "") for word in ["50%", "80%", "ALL", "满仓", "全部"]):
        mistake = "仓位过重"
    elif any(word in text + (current.worst_case_plan or "") for word in ["再看看", "没止损", "没有止损"]):
        mistake = "没有止损"

    lesson = "真正的问题不是判断错了，而是你有没有提前设计亏损时怎么办。"
    next_action = "下次买入前，先写失效条件、止损位置和最大可承受亏损。"
    return update_notebook(
        notebook_id,
        NotebookUpdate(
            status="Reviewed",
            mistakes=mistake,
            lesson=lesson,
            next_action=next_action,
            review_date=_now(),
            notes=((current.notes or "") + f"\n\nReview: {text}").strip(),
        ),
        user_id,
    )
