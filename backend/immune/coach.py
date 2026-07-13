import json
from typing import Any, Dict

from immune.direction import direction_label, normalize_trade_direction
from immune.outcome import outcome_rehearsal


def _load_report(entry: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(entry.get("full_report_json") or "{}")
    except json.JSONDecodeError:
        return {}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_any(text: str, words: list[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def build_ai_coach(entry: Dict[str, Any]) -> str:
    report = _load_report(entry)
    asset = entry.get("asset") or "这个资产"
    direction = normalize_trade_direction(entry.get("trade_direction") or report.get("trade_direction"))
    direction_text = direction_label(direction)
    emotion_score = _to_int(entry.get("emotion_score"))
    conviction_score = _to_int(entry.get("conviction_score"))
    bias_score = _to_int(entry.get("bias_score"))
    risk_score = _to_int(entry.get("risk_score"))
    position_size = entry.get("position_size") or ""
    worst_case = entry.get("worst_case_plan") or entry.get("notes") or ""
    favorable_plan = entry.get("favorable_plan") or ""
    sideways_plan = entry.get("sideways_plan") or ""
    user_text = " ".join(
        str(entry.get(field) or "")
        for field in [
            "user_intent",
            "user_text",
            "buy_reason",
            "risk_awareness",
            "notes",
            "worst_case_plan",
            "favorable_plan",
            "sideways_plan",
        ]
    )

    lines = [f"你现在记录的是：{asset}，方向是{direction_text}。"]

    if emotion_score >= 70:
        lines.append("AI看到的主要风险不是标的本身，而是情绪已经开始替你催单。")
    elif bias_score >= 60:
        lines.append("这条笔记里偏见信号偏强，先确认你是不是只在寻找支持自己观点的信息。")
    elif risk_score >= 70:
        lines.append("资产风险分已经偏高，任何方向都不能用大仓位去赌一次判断。")
    else:
        lines.append("结构比冲动交易好，但还需要把错误条件写得更具体。")

    if direction == "short":
        if _has_any(user_text, ["涨很多", "太高", "泡沫", "一定会跌", "做空"]):
            lines.append("做空最怕的不是你看错价值，而是行情继续上涨时你被迫止损或加空。")
        else:
            lines.append("做空前先写清楚：上涨多少你认错，而不是等亏损扩大后再解释。")
    elif direction == "long":
        if _has_any(user_text, ["怕踏空", "错过", "起飞", "涨很多", "再不上车"]):
            lines.append("做多前先分清：你是在研究机会，还是在缓解错过的焦虑。")
        else:
            lines.append("做多可以，但理由必须能经得起下跌时复盘。")

    if direction == "short":
        if favorable_plan and sideways_plan and worst_case:
            lines.append(f"你的三情景计划是：跌了按“{favorable_plan}”处理，横盘按“{sideways_plan}”处理，涨了按“{worst_case}”认错。")
        else:
            lines.append("Notebook 里还需要补齐三情景计划：跌了怎么止盈，横盘多久平仓，涨了多少认错。")
    else:
        if favorable_plan and sideways_plan and worst_case:
            lines.append(f"你的三情景计划是：涨了按“{favorable_plan}”处理，横盘按“{sideways_plan}”处理，跌了按“{worst_case}”退出。")
        else:
            lines.append("Notebook 里还需要补齐三情景计划：涨了怎么处理，横盘等多久，跌了哪里退出。")

    if conviction_score <= 40:
        lines.append(f"当前信念分只有 {conviction_score}，说明这还不像一套完整交易计划。")

    if _has_any(position_size, ["50%", "80%", "100%", "ALL IN", "all-in", "满仓", "全部", "重仓"]):
        lines.append(f"你写的仓位是 {position_size}。仓位过大时，普通波动会变成情绪事故。")

    if not worst_case or "再看看" in worst_case:
        lines.append("最需要补的一句是：价格到哪里、事实变成什么样，我就承认这笔交易失效。")
    elif len(str(worst_case)) < 12:
        lines.append(f"你的最坏情况计划是“{worst_case}”，还不够可执行，最好写成具体价格、比例或条件。")
    if favorable_plan and len(str(favorable_plan)) < 8:
        lines.append(f"你的有利情况计划是“{favorable_plan}”，还不够具体，最好写清楚分批止盈、继续持有或移动止损条件。")
    if sideways_plan and len(str(sideways_plan)) < 8:
        lines.append(f"你的横盘计划是“{sideways_plan}”，还不够具体，最好写清楚最长等待时间和重新评估条件。")

    decision_reason = report.get("decision_reason")
    if decision_reason:
        lines.append(str(decision_reason))

    return "\n\n".join(lines)
