from typing import Any, Dict, List

from immune.direction import direction_label
from schemas import ImmuneReportRequest


def _items(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _top_biases(report: Dict[str, Any]) -> List[str]:
    biases = report.get("bias_detection", {}).get("biases") or []
    result: List[str] = []
    for item in biases[:3]:
        if isinstance(item, dict):
            bias_type = item.get("bias_type") or "Unknown Bias"
            warning = item.get("warning") or item.get("better_question") or ""
            result.append(f"{bias_type}: {warning}".strip(": "))
        else:
            result.append(str(item))
    return result


def _market_snapshot(report: Dict[str, Any]) -> str:
    raw = report.get("risk_scan", {}).get("raw_data") or {}
    source = (
        raw.get("external_market_data_source")
        or raw.get("primary_data_source")
        or raw.get("source")
        or raw.get("data_source")
        or "fallback"
    )
    parts: List[str] = []

    price = raw.get("price_usd") or raw.get("price")
    if price:
        parts.append(f"价格 {price}")
    liquidity = raw.get("liquidity")
    if liquidity:
        parts.append(f"流动性 {liquidity}")
    volume = raw.get("volume24h") or raw.get("volume")
    if volume:
        parts.append(f"成交量 {volume}")
    fdv = raw.get("fdv") or raw.get("market_cap")
    if fdv:
        parts.append(f"估值/市值 {fdv}")

    if not parts:
        return f"数据源：{source}。当前只拿到有限行情字段，不能把它当作完整研究。"
    return f"数据源：{source}。" + "；".join(parts) + "。"


def _one_line_reason(report: Dict[str, Any]) -> str:
    decision = report.get("final_decision", "")
    emotion_score = int(report.get("emotion_scan", {}).get("emotion_score") or 0)
    bias_score = int(report.get("bias_detection", {}).get("bias_score") or 0)
    conviction = int(report.get("conviction_score", {}).get("score") or 0)
    confidence = int((report.get("data_confidence") or {}).get("score") or 0)

    if decision.startswith("🔴"):
        if emotion_score >= 70:
            return "你现在最大的问题不是资产本身，而是情绪正在推着你下单。"
        if bias_score >= 70:
            return "这次决策里偏差太重，先停下来比继续找理由更重要。"
        if conviction <= 40:
            return "你还没有写出足够清楚的交易计划，现在下单更像情绪下注。"
        return "当前风险组合不适合开仓，先让计划比观点更硬。"
    if confidence < 45:
        return "数据还不够完整，等待比用半截信息开仓更聪明。"
    if decision.startswith("🟢"):
        return "计划结构相对完整，但仍只能小仓位试错，不能把观点当确定性。"
    return "现在最好的动作不是立刻交易，而是补全证据和退出规则。"


def _format_list(items: List[str], fallback: str) -> str:
    values = [item for item in items if item]
    if not values:
        values = [fallback]
    return "\n".join(f"{index}. {item}" for index, item in enumerate(values, start=1))


def _format_bullets(items: List[str], fallback: str) -> str:
    values = [item for item in items if item]
    if not values:
        values = [fallback]
    return "\n".join(f"- {item}" for item in values)


def _build_display_markdown(
    payload: ImmuneReportRequest,
    result: Dict[str, Any],
    report: Dict[str, Any],
    what_is_missing: List[str],
) -> str:
    asset = result.get("asset") or payload.asset.upper()
    decision = result.get("decision") or report.get("final_decision")
    headline = result.get("headline") or _one_line_reason(report)
    confidence = result.get("data_confidence") or {}
    behavior = result.get("behavior_scan") or {}
    top_risks = _items(result.get("top_risks"))[:4]
    must_answer = _items(result.get("must_answer_before_trade"))[:3]
    emotions = _items(behavior.get("detected_emotions"))[:4]
    biases = _items(behavior.get("top_biases"))[:3]

    return "\n".join(
        [
            f"# {decision} {asset}",
            "",
            headline,
            "",
            "## 市场数据",
            f"- {result.get('market_snapshot')}",
            f"- 数据置信度：{confidence.get('score')} / {confidence.get('level')}",
            f"- 数据提示：{confidence.get('summary')}",
            "",
            "## 为什么现在不该冲动",
            _format_list(top_risks, "当前证据还不足以支持重仓开仓。"),
            "",
            "## 行为风险",
            f"- 情绪分：{behavior.get('emotion_score')}",
            f"- 识别情绪：{', '.join(emotions) if emotions else '未触发明显情绪标签'}",
            f"- 偏差分：{behavior.get('bias_score')}",
            f"- 主要偏差：{'; '.join(biases) if biases else '未触发明显偏差'}",
            f"- KOL 提醒：{behavior.get('kol_warning') or '未匹配到具体 KOL 画像，但仍要确认这是不是外部叙事驱动。'}",
            "",
            "## 下单前必须回答",
            _format_bullets(must_answer, "什么事实出现后，你会承认自己错了？"),
            "",
            "## 迷你投资笔记",
            f"- 开仓理由：{payload.buy_reason or payload.user_intent or '未填写'}",
            f"- 仓位规模：{payload.position_size or '未填写'}",
            f"- 最坏情况计划：{payload.worst_case_plan or '未填写'}",
            f"- 当前缺口：{'; '.join(what_is_missing[:4])}",
            "",
            "## 下一步",
            f"{result.get('next_step')}",
            "",
            "这不是预测价格的工具。它帮你在下单前停一下，在复盘后变聪明一点。",
        ]
    )


def build_okx_ai_agent_result(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    direction = direction_label(report.get("trade_direction") or payload.trade_direction)
    risk_reasons = _items(report.get("risk_scan", {}).get("risk_reasons"))[:4]
    emotions = _items(report.get("emotion_scan", {}).get("detected_emotions"))[:4]
    confidence = report.get("data_confidence") or {}
    coach = report.get("ai_coach") or {}
    history = report.get("historical_dna_scan") or {}
    kol_scan = report.get("kol_risk_scan") or {}

    must_answer = report.get("devil_advocate", {}).get("killer_questions") or []
    if not must_answer:
        must_answer = [
            "如果价格朝反方向走 25%，你会怎么处理？",
            "什么事实出现后，你会承认自己错了？",
            "这笔仓位亏损后，会不会影响下一次理性决策？",
        ]

    what_is_missing: List[str] = []
    for problem in _items(report.get("conviction_score", {}).get("problems"))[:3]:
        what_is_missing.append(problem)
    if confidence.get("missing"):
        what_is_missing.append("数据缺口：" + "、".join(_items(confidence.get("missing"))[:3]))
    if not what_is_missing:
        what_is_missing.append("继续保持：理由、仓位、反向情景和复盘条件都要写清楚。")

    result = {
        "service_name": "Investment Immune Scan",
        "designed_for": "OKX.AI A2MCP",
        "headline": _one_line_reason(report),
        "decision": report.get("final_decision"),
        "asset": report.get("asset"),
        "asset_type": report.get("asset_type"),
        "direction": direction,
        "market_snapshot": _market_snapshot(report),
        "data_confidence": {
            "score": confidence.get("score"),
            "level": confidence.get("level"),
            "summary": confidence.get("summary"),
        },
        "top_risks": risk_reasons,
        "behavior_scan": {
            "emotion_score": report.get("emotion_scan", {}).get("emotion_score"),
            "detected_emotions": emotions,
            "bias_score": report.get("bias_detection", {}).get("bias_score"),
            "top_biases": _top_biases(report),
            "kol_warning": kol_scan.get("warning") if isinstance(kol_scan, dict) else None,
        },
        "why_stop_or_wait": report.get("decision_reason"),
        "position_advice": report.get("position_advice"),
        "must_answer_before_trade": _items(must_answer)[:3],
        "mini_notebook": {
            "what_user_wrote": {
                "intent": payload.user_intent,
                "reason": payload.buy_reason,
                "position_size": payload.position_size,
                "worst_case_plan": payload.worst_case_plan,
                "favorable_plan": payload.favorable_plan,
                "sideways_plan": payload.sideways_plan,
            },
            "what_is_missing": what_is_missing,
            "review_later": "7 天后复盘：你是否按计划执行，而不是按情绪改规则。",
        },
        "mini_dna_update": {
            "historical_patterns": history.get("triggered_patterns", []),
            "risk_adjustment": history.get("risk_adjustment", 0),
            "summary": history.get("summary"),
        },
        "coach_message": coach.get("coach_message"),
        "next_step": coach.get("next_action") or "先等待 24 小时，再重新扫描同一个资产。",
        "full_product_url": "https://global-asset-shield.onrender.com",
    }
    result["short_answer"] = f"{result['decision']} {result['asset']}。{result['headline']}"
    result["recommended_display_field"] = "okx_ai_agent_result.display_markdown"
    result["demo_ready_summary"] = (
        f"{result['decision']} {result['asset']}：{result['headline']} "
        f"系统已综合市场数据、情绪风险、认知偏差、仓位风险和历史 DNA，给出下单前免疫提醒。"
    )
    result["display_markdown"] = _build_display_markdown(payload, result, report, what_is_missing)
    return result
