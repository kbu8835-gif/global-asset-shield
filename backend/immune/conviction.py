import re

from scanner.utils import clamp_score
from schemas import ImmuneReportRequest


def _has_clear_text(value: str | None) -> bool:
    return bool(value and len(value.strip()) >= 8)


def _position_percent(position_size: str | None) -> float | None:
    if not position_size:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", position_size)
    if match:
        return float(match.group(1))
    if any(word in position_size for word in ["满仓", "全部", "all"]):
        return 100.0
    return None


def build_conviction_score(payload: ImmuneReportRequest) -> dict:
    score = 0
    problems = []
    questions = []
    all_text = " ".join(
        [
            payload.buy_reason or "",
            payload.risk_awareness or "",
            payload.worst_case_plan or "",
            payload.user_text or "",
            payload.position_size or "",
        ]
    )

    if _has_clear_text(payload.buy_reason):
        score += 25
    else:
        problems.append("买入理由不清楚")
        questions.append("除了别人推荐和价格上涨，你自己的买入证据是什么？")

    if payload.risk_awareness and not any(word in payload.risk_awareness for word in ["不清楚", "不知道", "没想过"]):
        score += 25
    else:
        problems.append("没有说清最大风险")
        questions.append("这个资产最可能让你亏钱的机制是什么？")

    if payload.worst_case_plan and not any(word in payload.worst_case_plan for word in ["再看看", "不知道", "没想过"]):
        score += 25
    else:
        problems.append("没有明确止损或失效条件")
        questions.append("跌到什么程度或出现什么事实，你必须退出？")

    position = _position_percent(payload.position_size)
    if position is None or position <= 10:
        score += 25
    else:
        problems.append("仓位过大")
        questions.append("为什么这笔交易值得一次押上超过 10% 的资金？")

    if any(word in all_text for word in ["KOL推荐", "朋友推荐", "朋友说", "大V说"]):
        score -= 25
        problems.append("买入理由依赖他人推荐")
    if any(word in all_text for word in ["会涨", "十倍", "百倍", "起飞"]):
        score -= 25
        problems.append("理由偏向上涨口号，不是可验证逻辑")
    if any(word in all_text for word in ["不知道风险", "不清楚风险", "不太清楚风险"]):
        score -= 25
        problems.append("风险意识不足")
    if not payload.worst_case_plan:
        score -= 25
    if position is not None and position > 30:
        score -= 20

    score = clamp_score(score)
    if score <= 25:
        level = "无信念"
    elif score <= 50:
        level = "弱信念"
    elif score <= 75:
        level = "中等信念"
    else:
        level = "强信念"

    if not questions:
        questions = [
            "这笔交易的失效条件是否能被外部事实验证？",
            "如果先跌 30%，你是否仍按同一计划执行？",
        ]

    return {
        "score": score,
        "level": level,
        "problems": list(dict.fromkeys(problems)),
        "improvement_questions": questions,
    }

