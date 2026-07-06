from database import get_journal_entry, mark_reviewed
from schemas import ReviewRequest, ReviewResponse


def _mistake_type(entry, text: str) -> str:
    combined = f"{entry.user_intent or ''} {entry.user_text or ''} {entry.buy_reason or ''} {text}"
    if any(word in combined for word in ["怕踏空", "错过", "涨很多", "起飞"]):
        return "FOMO 追高"
    if any(word in combined for word in ["KOL", "大V", "老师说", "喊单"]):
        return "KOL 盲从"
    if any(word in combined for word in ["50%", "80%", "满仓", "梭哈", "全部"]):
        return "仓位过重"
    if any(word in combined for word in ["再看看", "没有止损", "没止损"]):
        return "没有止损"
    if any(word in combined for word in ["补仓", "回本", "舍不得割肉"]):
        return "沉没成本"
    if entry.conviction_score <= 40:
        return "没有风险意识"
    return "逻辑正确但市场波动"


def review_journal(payload: ReviewRequest, user_id: int) -> ReviewResponse:
    entry = get_journal_entry(payload.journal_id, user_id)
    if entry is None:
        raise ValueError("journal entry not found")

    mistake = _mistake_type(entry, payload.user_result_text)
    if mistake == "FOMO 追高":
        lesson = "一个月前你追的是上涨带来的安全感，不是经过验证的机会。"
        rule = "下次凡是出现怕踏空，必须等 24 小时，并写出三个不买理由。"
    elif mistake == "KOL 盲从":
        lesson = "真正的问题不是 KOL 判断错了，而是你把别人的观点当成了自己的风控。"
        rule = "下次任何喊单都必须补齐成本、仓位、退出计划和反方证据。"
    elif mistake == "仓位过重":
        lesson = "仓位把普通错误放大成情绪灾难。你不是需要更准，你是需要活得更久。"
        rule = "没有强信念和失效条件时，单笔不超过 5%。"
    elif mistake == "没有止损":
        lesson = "你没有设计亏损时怎么办，所以市场替你设计了代价。"
        rule = "买入前必须写下失效条件，否则不允许下单。"
    elif mistake == "沉没成本":
        lesson = "你不是在修正判断，你是在用更多钱维护自尊。"
        rule = "补仓前先问：如果今天没有持仓，我还会买它吗？"
    elif mistake == "没有风险意识":
        lesson = "真正的问题不是判断错了，而是你没有认真定义风险。"
        rule = "每笔交易必须先写最大亏损和退出条件，再写收益想象。"
    else:
        lesson = "有些亏损来自市场波动，但复盘仍要检查仓位和执行是否合格。"
        rule = "保留交易前记录，用事实区分逻辑错误和正常波动。"

    review_result = f"{payload.user_result_text}。复盘结论：{lesson}"
    mark_reviewed(payload.journal_id, user_id)
    return ReviewResponse(
        journal_id=payload.journal_id,
        original_decision=entry.final_decision,
        review_result=review_result,
        mistake_type=mistake,
        lesson=lesson,
        next_time_rule=rule,
        review_status="reviewed",
    )
