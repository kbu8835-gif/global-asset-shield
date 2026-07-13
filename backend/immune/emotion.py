from scanner.utils import clamp_score
from schemas import ImmuneReportRequest


def _combined_text(payload: ImmuneReportRequest) -> str:
    return " ".join(
        [
            payload.user_intent or "",
            payload.user_text or "",
            payload.buy_reason or "",
            payload.risk_awareness or "",
            payload.favorable_plan or "",
            payload.sideways_plan or "",
            payload.worst_case_plan or "",
            payload.position_size or "",
            payload.horizon or "",
            payload.trade_direction or "",
        ]
    )


def _emotion_level(score: int) -> str:
    if score <= 25:
        return "冷静"
    if score <= 50:
        return "轻微冲动"
    if score <= 75:
        return "明显冲动"
    return "高度冲动"


def scan_emotion(payload: ImmuneReportRequest) -> dict:
    text = _combined_text(payload)
    normalized = text.replace(" ", "")
    score = 0
    detected = []

    rules = [
        (["怕踏空", "错过", "涨很多", "起飞"], "FOMO", 30),
        (["梭哈", "满仓", "重仓", "50%", "80%", "全部"], "仓位冲动", 30),
        (["朋友推荐"], "社交驱动", 20),
        (["KOL", "kol", "博主", "大V", "喊单"], "KOL 驱动", 25),
        (["亏了", "补仓", "回本"], "亏损厌恶/沉没成本", 30),
        (["不知道风险", "不清楚风险", "不太清楚风险"], "风险无知", 20),
        (["做空", "开空", "short", "看跌", "必跌", "归零", "跌爆"], "做空冲动", 25),
        (["报复", "干回来", "爆仓后", "亏回来"], "报复性交易", 25),
    ]

    for keywords, label, points in rules:
        if any(keyword in normalized for keyword in keywords):
            score += points
            detected.append(label)

    if not detected:
        detected.append("不清楚")
        score = 20

    score = clamp_score(score)
    if score >= 75:
        advice = "先停手。你现在最需要的不是更快下单，而是把最坏情况写清楚。"
    elif score >= 50:
        advice = "等待 24 小时，把仓位降到你睡得着的水平，再重新看这笔交易。"
    else:
        advice = "情绪温度可控，但仍要写出失效条件。说不出失效条件，就不要买。"

    return {
        "emotion_score": score,
        "emotion_level": _emotion_level(score),
        "detected_emotions": detected,
        "intervention_advice": advice,
    }
