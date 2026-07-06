def simulate_regret(asset: str, emotion_score: int, bias_detection: dict, position_size: str | None = None) -> dict[str, str]:
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

    return {
        "buy_and_up": f"买了 {asset} 后上涨：你会开心，但容易把运气当能力，下一次加大仓位。",
        "buy_and_down": "买了后下跌：你会急着找理由补仓，或者恐慌割肉。提前写规则能救你。",
        "not_buy_and_up": "没买却上涨：你会难受，但错过不是亏损，本金还在就是下一次机会。",
        "not_buy_and_down": "没买且下跌：你保住本金，也证明等待本身是一种能力。",
        "likely_regret_pattern": likely,
        "behavior_warning": warning,
    }

