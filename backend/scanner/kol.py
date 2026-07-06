import json
from datetime import datetime, timezone
from typing import List

from config import KOL_RECORDS_PATH
from schemas import KOLCheckRequest, KOLCheckResponse


RISK_WORDS = ["梭哈", "稳赚", "内幕", "翻倍", "怕踏空", "暴富", "无脑买", "KOL推荐", "起飞", "喊单"]


def _load_calls() -> List[dict]:
    if not KOL_RECORDS_PATH.exists():
        return []
    with KOL_RECORDS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_calls(calls: List[dict]) -> None:
    KOL_RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with KOL_RECORDS_PATH.open("w", encoding="utf-8") as file:
        json.dump(calls, file, ensure_ascii=False, indent=2, default=str)


def check_kol_call(payload: KOLCheckRequest) -> KOLCheckResponse:
    text = payload.call_text
    risk_hits = [word for word in RISK_WORDS if word.lower() in text.lower()]
    credibility_score = max(0, 72 - len(risk_hits) * 11)
    result = "高风险喊单" if credibility_score < 45 else "需要观察" if credibility_score < 65 else "普通记录"
    reasons = [f"喊单内容包含高风险词：{word}" for word in risk_hits]

    if payload.price_at_call and payload.current_price:
        change = (payload.current_price - payload.price_at_call) / payload.price_at_call
        if change < -0.2:
            credibility_score = max(0, credibility_score - 15)
            result = "历史表现偏弱"
            reasons.append("喊单后价格下跌超过 20%")
        elif change > 0.2:
            credibility_score = min(100, credibility_score + 8)
            reasons.append("喊单后价格上涨超过 20%，但样本太少不能证明能力")

    if not reasons:
        reasons.append("本地规则未发现明显喊单风险词")

    response = KOLCheckResponse(
        kol_name=payload.kol_name,
        asset=payload.asset.upper(),
        call_text=payload.call_text,
        call_time=payload.call_time or datetime.now(timezone.utc),
        price_at_call=payload.price_at_call,
        current_price=payload.current_price,
        result=result,
        credibility_score=credibility_score,
        risk_reasons=reasons,
    )

    calls = _load_calls()
    calls.append(response.model_dump(mode="json"))
    _save_calls(calls)
    return response

