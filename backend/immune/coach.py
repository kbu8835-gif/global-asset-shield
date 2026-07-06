import json
from typing import Any, Dict


def _load_report(entry: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(entry.get("full_report_json") or "{}")
    except json.JSONDecodeError:
        return {}


def build_ai_coach(entry: Dict[str, Any]) -> str:
    report = _load_report(entry)
    asset = entry.get("asset") or "这个资产"
    emotion_score = entry.get("emotion_score") or 0
    conviction_score = entry.get("conviction_score") or 0
    bias_score = entry.get("bias_score") or 0
    position_size = entry.get("position_size") or ""
    worst_case = entry.get("worst_case_plan") or entry.get("notes") or ""

    lines = [f"你的问题不一定是：{asset}。"]

    if emotion_score >= 70:
        lines.append("而是：你把上涨当成了安全感。")
    elif bias_score >= 60:
        lines.append("而是：你让叙事替你完成了判断。")
    else:
        lines.append("而是：你需要先写清楚自己为什么会错。")

    if conviction_score <= 40:
        lines.append("你今天没有写出足够硬的买入逻辑。")

    if any(word in position_size for word in ["50%", "80%", "ALL", "all", "满仓", "全部"]):
        lines.append("仓位太大时，普通波动会变成情绪事故。")

    if not worst_case or "再看看" in worst_case:
        lines.append("真正优秀的投资者，先写止损，再下单。")

    decision_reason = report.get("decision_reason")
    if decision_reason:
        lines.append(str(decision_reason))

    return "\n\n".join(lines)

