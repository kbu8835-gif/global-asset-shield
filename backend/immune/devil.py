def build_devil_advocate(asset: str, asset_type: str, risk_scan: dict, emotion_scan: dict, bias_detection: dict) -> dict:
    against = [
        f"如果我是反方，我会反对你现在买 {asset}，因为当前风险分是 {risk_scan['risk_score']}，这不是低噪音环境。",
        "你的最大风险不是这个资产会不会跌，而是你没有想过它跌了以后怎么办。",
        "如果你说不出失效条件，这不是投资，这是情绪下注。",
        "市场不会因为你害怕错过就给你更好的买点。冲动买入通常把风控放在最后。",
    ]

    bias_types = {item["bias_type"] for item in bias_detection.get("biases", [])}
    if "FOMO" in bias_types or "FOMO" in emotion_scan.get("detected_emotions", []):
        against.append("你现在可能不是在研究机会，而是在逃避错过的焦虑。")
    if asset_type == "crypto":
        against.append("Crypto 的流动性可以在你想卖时消失，盘口深度比叙事更诚实。")
    else:
        against.append("热门股票的好公司和好买点不是一回事，估值过热时也会伤人。")

    supporting = [
        "支持买入的理由可能是：你有独立研究，并且能写出明确的失效条件。",
        "支持买入的理由可能是：仓位很小，小到即使错了也不会影响你的长期本金。",
    ]

    killer = [
        "如果明天跌 30%，你会怎么做？",
        "谁可能正在把筹码卖给你，为什么他愿意卖？",
        "什么事实出现后，你会承认自己错了？",
        "这笔仓位亏光，会不会影响你下一次理性决策？",
    ]

    return {
        "against_buying": against[:6],
        "supporting_case": supporting,
        "killer_questions": killer,
    }

