from typing import Optional


DIRECTION_LABELS = {
    "long": "做多",
    "short": "做空",
    "watch": "观望",
}


def normalize_trade_direction(value: Optional[str]) -> str:
    text = (value or "long").strip().lower()
    mapping = {
        "buy": "long",
        "long": "long",
        "做多": "long",
        "买入": "long",
        "看涨": "long",
        "sell": "short",
        "short": "short",
        "做空": "short",
        "开空": "short",
        "看跌": "short",
        "空": "short",
        "wait": "watch",
        "watch": "watch",
        "observe": "watch",
        "观望": "watch",
        "先观察": "watch",
    }
    return mapping.get(text, text if text in DIRECTION_LABELS else "long")


def direction_label(value: Optional[str]) -> str:
    return DIRECTION_LABELS.get(normalize_trade_direction(value), "做多")


def direction_action_text(value: Optional[str]) -> str:
    direction = normalize_trade_direction(value)
    if direction == "short":
        return "做空"
    if direction == "watch":
        return "观望"
    return "买入"
