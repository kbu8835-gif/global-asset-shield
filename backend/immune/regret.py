def simulate_regret(
    asset: str,
    emotion_score: int,
    bias_detection: dict,
    position_size: str | None = None,
    trade_direction: str = "long",
    payload=None,
) -> dict[str, str]:
    bias_types = {item["bias_type"] for item in bias_detection.get("biases", [])}
    favorable_plan = getattr(payload, "favorable_plan", None) or ""
    sideways_plan = getattr(payload, "sideways_plan", None) or ""
    worst_case_plan = getattr(payload, "worst_case_plan", None) or ""
    buy_reason = getattr(payload, "buy_reason", None) or ""
    if "Sunk Cost" in bias_types:
        likely = "容易越跌越补，不愿承认错误"
    elif emotion_score > 70:
        likely = "容易追高后恐慌卖出"
    else:
        likely = "主要风险是复盘不足，把结果误当能力"

    size_text = position_size or ""
    if any(word in size_text for word in ["50%", "80%", "100%", "全部", "满仓", "ALL IN", "all in"]):
        warning = f"你写的仓位是 {position_size}，后悔不会来自方向错一次，而是来自一次错判伤到本金结构。"
    else:
        warning = f"你写的仓位是 {position_size or '未填写'}。真正降低后悔的方式不是猜对方向，而是让错误可承受。"

    if trade_direction == "short":
        return {
            "buy_and_up": f"做空 {asset} 后上涨：最重要的是按“{worst_case_plan or '止损线'}”认错，不要把亏损解释成更好的加空机会。",
            "buy_and_down": f"做空后下跌：你会开心，但要按“{favorable_plan or '止盈计划'}”处理盈利，别让贪婪把盈利变回亏损。",
            "not_buy_and_up": "没做空且上涨：你躲过一次可能失控的逼空，等待不是错过，是避免被波动教育。",
            "not_buy_and_down": f"没做空却下跌：你会后悔，尤其当理由是“{buy_reason or '看空判断'}”时。但没有执行计划的利润，不属于你。",
            "likely_regret_pattern": "容易因为看空情绪过强，在逼空时加码硬扛" if emotion_score > 70 else f"最可能的后悔点是没有按“{favorable_plan or '止盈计划'}”处理盈利，或没有按“{worst_case_plan or '止损线'}”认错。",
            "behavior_warning": warning.replace("仓位", "空头仓位") if "仓位" in warning else warning,
        }
    if trade_direction == "watch":
        return {
            "buy_and_up": f"观望后 {asset} 上涨：你会感到错过，但这能训练你只在规则内行动。",
            "buy_and_down": "观望后下跌：你保住本金，也验证了不急着开仓的价值。",
            "not_buy_and_up": "没开仓却上涨：真正要复盘的是你的触发条件是否太苛刻，而不是临时追单。",
            "not_buy_and_down": "没开仓且下跌：等待帮你避免了一次情绪下注。",
            "likely_regret_pattern": "容易把观察变成临场追单，需要提前写触发条件",
            "behavior_warning": "观望不是空白状态。写下复查时间和触发条件，才是真正的等待。",
        }
    return {
        "buy_and_up": f"买了 {asset} 后上涨：你会开心，但要按“{favorable_plan or '盈利计划'}”处理，不要把一次顺利当成下次加仓理由。",
        "buy_and_down": f"买了后下跌：真正考验是能否按“{worst_case_plan or '退出计划'}”执行，而不是补仓证明自己没错。",
        "not_buy_and_up": "没买却上涨：你会难受，但错过不是亏损，本金还在就是下一次机会。",
        "not_buy_and_down": f"没买且下跌：你保住本金，也证明等待到“{sideways_plan or '复查条件'}”本身是一种能力。",
        "likely_regret_pattern": f"{likely}；这次要重点复盘你有没有按三情景计划执行。",
        "behavior_warning": warning,
    }
