from schemas import ImmuneReportRequest


def build_observation_plan(payload: ImmuneReportRequest, asset: str) -> dict:
    signal = (payload.risk_awareness or "").strip() or "还没有写清楚观察信号"
    fomo_plan = (payload.worst_case_plan or "").strip() or "如果价格突然大涨，先重新扫描，不临时追单"
    horizon = (payload.horizon or "").strip() or "24 小时"

    missing = []
    if not payload.risk_awareness:
        missing.append("观察信号")
    if not payload.worst_case_plan:
        missing.append("突然波动时的行动规则")

    rules = [
        f"在 {signal} 出现之前，不开仓。",
        f"如果 {asset} 突然大涨或大跌，执行原计划：{fomo_plan}。",
        f"{horizon} 后回来复查一次，不在情绪最热的时候做决定。",
    ]
    if payload.position_size:
        rules.append(f"如果最后决定试错，仓位上限仍然按 {payload.position_size} 重新评估，不自动放大。")

    return {
        "mode": "watch",
        "signal_to_watch": signal,
        "fomo_plan": fomo_plan,
        "review_timing": horizon,
        "no_position_rule": "观望期间不追单、不补情绪单、不因为 KOL 新消息临时开仓。",
        "checklist": rules,
        "missing_items": missing,
        "summary": f"观望不是空等。你现在需要等 {signal}，而不是用价格波动逼自己立刻表态。",
    }
