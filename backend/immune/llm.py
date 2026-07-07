import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import requests

from config import (
    DEEPSEEK_API_BASE,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    LLM_DAILY_LIMIT,
    LLM_ENABLED,
    LLM_TIMEOUT_SECONDS,
)
from database import get_connection, init_db
from schemas import ImmuneReportRequest


FEATURE_IMMUNE_COACH = "immune_report_ai_coach"


def build_ai_coach(payload: ImmuneReportRequest, report: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    fallback = fallback_ai_coach(payload, report)
    if not LLM_ENABLED:
        return _with_meta(fallback, "disabled", False, LLM_DAILY_LIMIT, _remaining_quota(user_id))
    if not DEEPSEEK_API_KEY:
        return _with_meta(fallback, "fallback_no_api_key", False, LLM_DAILY_LIMIT, _remaining_quota(user_id))

    allowed, remaining = consume_llm_quota(user_id, FEATURE_IMMUNE_COACH)
    if not allowed:
        fallback["next_action"] = "今天的 AI 教练调用次数已经用完。继续扫描仍会返回规则版报告，明天会自动恢复额度。"
        return _with_meta(fallback, "limit_exceeded", False, LLM_DAILY_LIMIT, remaining)

    try:
        ai_result = _call_deepseek(payload, report)
        return _with_meta(ai_result, "deepseek", True, LLM_DAILY_LIMIT, remaining)
    except Exception as exc:
        fallback["error"] = str(exc)[:180]
        return _with_meta(fallback, "fallback_error", False, LLM_DAILY_LIMIT, remaining)


def fallback_ai_coach(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    final_decision = report.get("final_decision", "")
    conviction = report.get("conviction_score", {}).get("score", 0)
    emotion_score = report.get("emotion_scan", {}).get("emotion_score", 0)
    bias_score = report.get("bias_detection", {}).get("bias_score", 0)
    kol_detected = bool(report.get("kol_risk_scan"))

    if "Don't Buy" in final_decision:
        coach_message = "先停手。你现在最需要的不是更快下单，而是写清楚什么情况下你承认自己错了。"
    elif "Wait" in final_decision:
        coach_message = "先观察。能等 24 小时的人，通常已经赢过了最冲动的自己。"
    else:
        coach_message = "如果真的要试，只能小仓位。先让计划保护你，再让观点参与市场。"

    if kol_detected:
        behavior_pattern = "这次决策有明显 KOL 驱动。真正的风险不是这个 KOL 看没看对，而是你可能把判断外包给了别人。"
    elif emotion_score >= 70:
        behavior_pattern = "你现在可能不是在研究机会，而是在缓解错过或回本的焦虑。"
    elif bias_score >= 60:
        behavior_pattern = "你的问题不是没有信息，而是已经带着结论在筛选信息。"
    elif conviction <= 40:
        behavior_pattern = "你还没有形成真正的买入逻辑。说不出失效条件，这不是投资，是情绪下注。"
    else:
        behavior_pattern = "这次输入相对冷静，但仍要把仓位、退出条件和复盘时间写下来。"

    return {
        "coach_message": coach_message,
        "behavior_pattern": behavior_pattern,
        "next_action": "先写下：买入理由、最大亏损、失效条件、仓位上限。写不出来，就不要买。",
    }


def consume_llm_quota(user_id: int, feature: str) -> Tuple[bool, int]:
    init_db()
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM llm_usage WHERE user_id = ? AND usage_date = ? AND feature = ? ORDER BY id ASC LIMIT 1",
            (user_id, today, feature),
        ).fetchone()
        current_count = int(row["call_count"]) if row else 0
        if current_count >= LLM_DAILY_LIMIT:
            return False, 0
        if row:
            conn.execute(
                "UPDATE llm_usage SET call_count = ?, updated_at = ? WHERE id = ?",
                (current_count + 1, now, int(row["id"])),
            )
        else:
            conn.execute(
                "INSERT INTO llm_usage (user_id, usage_date, feature, call_count, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, today, feature, 1, now),
            )
        conn.commit()
    return True, max(LLM_DAILY_LIMIT - current_count - 1, 0)


def _remaining_quota(user_id: int) -> int:
    init_db()
    today = datetime.now(timezone.utc).date().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT call_count FROM llm_usage WHERE user_id = ? AND usage_date = ? AND feature = ? ORDER BY id ASC LIMIT 1",
            (user_id, today, FEATURE_IMMUNE_COACH),
        ).fetchone()
    current_count = int(row["call_count"]) if row else 0
    return max(LLM_DAILY_LIMIT - current_count, 0)


def _call_deepseek(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = DEEPSEEK_API_BASE.rstrip("/") + "/chat/completions"
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 Global Asset Shield 的 AI 投资免疫教练。"
                    "你不预测价格，不迎合用户，不说“自行判断”。"
                    "你只根据给定 JSON 识别行为风险，并输出严格 JSON。"
                    "语气直接、有洞察、像风控教练。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(_compact_context(payload, report), ensure_ascii=False),
            },
        ],
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 420,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json=body,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"DeepSeek API returned {response.status_code}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _parse_json_content(content)
    return {
        "coach_message": str(parsed.get("coach_message") or "").strip() or "先停手，把计划写清楚再考虑下单。",
        "behavior_pattern": str(parsed.get("behavior_pattern") or "").strip() or "你的行为风险需要先被看见，再谈资产机会。",
        "next_action": str(parsed.get("next_action") or "").strip() or "写下失效条件、仓位上限和复盘日期。",
    }


def _compact_context(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": "请输出 JSON，字段为 coach_message, behavior_pattern, next_action。每个字段不超过 80 个中文字符。",
        "asset": report.get("asset"),
        "asset_type": report.get("asset_type"),
        "user_input": payload.model_dump(),
        "scores": {
            "risk_score": report.get("risk_scan", {}).get("risk_score"),
            "emotion_score": report.get("emotion_scan", {}).get("emotion_score"),
            "bias_score": report.get("bias_detection", {}).get("bias_score"),
            "conviction_score": report.get("conviction_score", {}).get("score"),
            "final_decision": report.get("final_decision"),
        },
        "risk_reasons": report.get("risk_scan", {}).get("risk_reasons", [])[:5],
        "detected_emotions": report.get("emotion_scan", {}).get("detected_emotions", [])[:5],
        "biases": report.get("bias_detection", {}).get("biases", [])[:5],
        "kol_risk_scan": report.get("kol_risk_scan"),
        "munger_lens": report.get("munger_lens"),
        "position_advice": report.get("position_advice"),
    }


def _parse_json_content(content: str) -> Dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def _with_meta(result: Dict[str, Any], source: str, enabled: bool, daily_limit: int, remaining: int) -> Dict[str, Any]:
    enriched = dict(result)
    enriched.update(
        {
            "enabled": enabled,
            "source": source,
            "model": DEEPSEEK_MODEL if enabled else None,
            "daily_limit": daily_limit,
            "remaining": remaining,
            "fallback_used": source != "deepseek",
            "cost_control": f"每个用户每天最多 {daily_limit} 次 AI 教练调用；失败或超额时自动返回规则版报告。",
        }
    )
    return enriched
