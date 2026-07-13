import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_connection, init_db
from immune.coach import build_ai_coach
from immune.direction import normalize_trade_direction
from immune.outcome import analyze_review_outcome
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
        favorable_plan=row.get("favorable_plan"),
        sideways_plan=row.get("sideways_plan"),
        position_size=row.get("position_size"),
        notes=row.get("notes"),
        mistakes=row.get("mistakes"),
        lesson=row.get("lesson"),
        next_action=row.get("next_action"),
        review_result_text=row.get("review_result_text"),
        review_outcome_label=row.get("review_outcome_label"),
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
                favorable_plan, sideways_plan, position_size, risk_score, emotion_score, bias_score, conviction_score,
                decision, final_decision, summary, full_report_json, review_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload.favorable_plan or "",
                payload.sideways_plan or "",
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
        "favorable_plan",
        "sideways_plan",
        "position_size",
        "mistakes",
        "lesson",
        "next_action",
        "review_result_text",
        "review_outcome_label",
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


def _contains(text: str, words: List[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _direction_review_prefix(direction: str) -> str:
    if direction == "short":
        return "这次做空复盘的重点不是证明你看空有道理，而是检查你有没有提前写清楚上涨多少就认错。"
    if direction == "watch":
        return "这次观察复盘的重点不是后悔有没有开仓，而是检查你当时等待的触发条件是否清楚。"
    return "这次做多复盘的重点不是证明你看多有道理，而是检查你有没有提前写清楚下跌后怎么办。"


def _review_outcome_tone(text: str) -> str:
    if _contains(text, ["卖飞", "卖早", "平早", "提前止盈", "提前平"]):
        return "这次最该复盘的不是方向判断，而是盈利处理是否过早。"
    if _contains(text, ["止损", "按计划", "认错"]):
        return "这次复盘重点是执行质量：你是否按计划行动，而不是事后重新解释。"
    if _contains(text, ["亏", "跌", "-"]):
        return "结果给了你一次压力测试。"
    if _contains(text, ["赚", "涨", "盈利", "+"]):
        return "结果看起来有利，但盈利不能自动证明过程正确。"
    if len(text.strip()) < 8:
        return "结果描述比较短，但已经能看出一个行为线索。以后最好补上动作和原因。"
    return "复盘要抓住真实动作：你当时做了什么，是否符合原计划。"


def review_notebook(notebook_id: int, payload: NotebookReviewRequest, user_id: int) -> Optional[NotebookDetail]:
    current = get_notebook(notebook_id, user_id)
    if current is None:
        return None
    text = payload.user_result_text
    combined = " ".join(
        [
            text,
            current.user_text or "",
            current.buy_reason or "",
            current.position_size or "",
            current.worst_case_plan or "",
            current.risk_awareness or "",
            current.notes or "",
            current.favorable_plan or "",
            current.sideways_plan or "",
        ]
    )
    direction = normalize_trade_direction(current.trade_direction)
    outcome = analyze_review_outcome(text, direction)

    mistake = "逻辑正确但执行条件不够清楚"
    if _contains(combined, ["再看看", "没止损", "没有止损", "没想好", "不知道怎么办"]):
        mistake = "没有止损"
    elif outcome:
        mistake = outcome["mistake"]
    elif _contains(combined, ["怕踏空", "追高", "涨很多", "起飞", "错过"]):
        mistake = "FOMO 追高"
    elif _contains(combined, ["KOL", "大V", "喊单", "老师", "群里", "朋友推荐"]):
        mistake = "外部观点替代计划"
    elif direction == "short" and _contains(combined, ["逼空", "反弹", "上涨", "爆仓", "加空"]):
        mistake = "做空风险低估"
    elif direction == "watch" and _contains(combined, ["后悔", "没买", "错过"]):
        mistake = "观察条件不清"
    elif _contains(current.position_size or "", ["50%", "80%", "100%", "ALL IN", "all-in", "满仓", "全部", "重仓"]) or _contains(
        text,
        ["all in", "满仓", "全部仓位", "重仓"],
    ):
        mistake = "仓位过重"

    lesson_parts = [_direction_review_prefix(direction), _review_outcome_tone(text)]
    if outcome:
        lesson_parts.append(f"你描述的结果像是：{outcome['market']}后{outcome['behavior']}。{outcome['lesson']}")
    if current.position_size:
        lesson_parts.append(f"你当时写的仓位是 {current.position_size}，复盘时要先问这是不是让情绪变大的原因。")
    if current.worst_case_plan:
        lesson_parts.append(f"你当时的最坏情况计划是“{current.worst_case_plan}”，检查它是否真的能执行，而不是事后安慰。")
    else:
        lesson_parts.append("这条记录缺少最坏情况计划，所以复盘时最该补的是退出条件。")
    if current.favorable_plan:
        lesson_parts.append(f"你当时写的有利情况计划是“{current.favorable_plan}”，复盘时检查盈利处理是否按计划执行。")
    if current.sideways_plan:
        lesson_parts.append(f"你当时写的横盘计划是“{current.sideways_plan}”，复盘时检查自己有没有被无聊逼着乱动。")
    lesson = " ".join(lesson_parts)

    if direction == "short":
        next_action = "下次做空前，先写完整三条：跌了怎么止盈，横盘多久平仓，涨到哪里认错。写不出来，就不要开空。"
    elif direction == "watch":
        next_action = "下次观察前，先写：什么数据出现才行动，什么风险确认就继续等待。"
    else:
        next_action = "下次做多前，先写：失效条件、止损位置、最大可承受亏损和是否允许补仓。"
    if outcome:
        next_action = outcome["next_action"]

    if mistake == "FOMO 追高":
        next_action = "下次出现怕踏空时，先等一个冷静周期，再写清楚不买也能接受的理由。"
    elif mistake == "外部观点替代计划":
        next_action = "下次看到 KOL 或朋友观点时，必须先写自己的失效条件；写不出，就只能记录，不能开仓。"
    elif mistake == "仓位过重":
        next_action = "下次先把仓位上限写死。超过计划仓位的交易，一律延迟 24 小时。"
    elif mistake == "没有止损":
        next_action = "下次开仓前先写退出条件；如果只有“再看看”，这笔交易自动不合格。"

    review_outcome_label = f"{outcome['market']}后{outcome['behavior']}" if outcome else mistake
    if mistake in {"没有止损", "FOMO 追高", "外部观点替代计划", "仓位过重", "观察条件不清"}:
        review_outcome_label = mistake

    return update_notebook(
        notebook_id,
        NotebookUpdate(
            status="Reviewed",
            mistakes=mistake,
            lesson=lesson,
            next_action=next_action,
            review_result_text=text,
            review_outcome_label=review_outcome_label,
            review_date=_now(),
        ),
        user_id,
    )
