def simulate_regret(
    asset: str,
    emotion_score: int,
    bias_detection: dict,
    position_size: str | None = None,
    trade_direction: str = "long",
) -> dict[str, str]:
    bias_types = {item["bias_type"] for item in bias_detection.get("biases", [])}
    if "Sunk Cost" in bias_types:
        likely = "容易越跌越补，不愿承认错误"
    elif emotion_score > 70:
        likely = "容易追高后恐慌卖出"
    else:
        likely = "主要风险是复盘不足，把结果误当能力"

    size_text = position_size or ""
    if any(word in size_text for word in ["50%", "80%", "全部", "满仓"]):
        warning = "仓位过高会把一次判断错误放大成长期伤害。先把仓位降下来，再谈观点。"
    else:
        warning = "真正降低后悔的方式不是猜对方向，而是让错误可承受。"

    if trade_direction == "short":
        return {
            "buy_and_up": f"做空 {asset} 后上涨：你会承受逼空压力，最危险的是为了证明自己没错而加空。",
            "buy_and_down": "做空后下跌：你会觉得自己看穿市场，但下一次可能忽略止盈和反弹风险。",
            "not_buy_and_up": "没做空且上涨：你躲过一次可能失控的亏损，等待不是错过，是避免被波动教育。",
            "not_buy_and_down": "没做空却下跌：你会后悔，但没有计划的利润不属于你。先练规则，再谈方向。",
            "likely_regret_pattern": "容易因为看空情绪过强，在逼空时加码硬扛" if emotion_score > 70 else likely,
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
        "buy_and_up": f"买了 {asset} 后上涨：你会开心，但容易把运气当能力，下一次加大仓位。",
        "buy_and_down": "买了后下跌：你会急着找理由补仓，或者恐慌割肉。提前写规则能救你。",
        "not_buy_and_up": "没买却上涨：你会难受，但错过不是亏损，本金还在就是下一次机会。",
        "not_buy_and_down": "没买且下跌：你保住本金，也证明等待本身是一种能力。",
        "likely_regret_pattern": likely,
        "behavior_warning": warning,
    }
