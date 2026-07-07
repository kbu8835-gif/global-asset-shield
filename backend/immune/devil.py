def _money(value) -> str:
    try:
        if value is None:
            return "未知"
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "未知"


def _percent(value) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _market_context(asset_type: str, raw: dict) -> list[str]:
    if not raw:
        return ["这份报告缺少可验证行情数据，不能把模板判断当作真实研究。"]

    if asset_type == "crypto":
        context = [
            f"当前交易对数据显示：价格 {raw.get('price_usd') or '未知'}，流动性 {_money(raw.get('liquidity'))}，FDV {_money(raw.get('fdv'))}，24h 成交量 {_money(raw.get('volume24h'))}。",
        ]
        if raw.get("fallback_mock"):
            context.append("这次没有拿到可靠 DexScreener 数据，报告只能作为行为风控提醒，不能当成链上尽调。")
        elif raw.get("liquidity") is not None and float(raw.get("liquidity") or 0) < 50_000:
            context.append("这个池子的退出深度很薄，你以为自己买的是叙事，真正成交时面对的是盘口。")
        if raw.get("pair_url"):
            context.append(f"买入前先打开交易对链接复核盘口：{raw.get('pair_url')}")
        return context

    context = [
        f"当前股票数据显示：价格 {raw.get('price') or '未知'}，市值 {_money(raw.get('market_cap'))}，单日涨跌幅 {_percent(raw.get('day_change_percent'))}，PE {raw.get('pe') if raw.get('pe') is not None else '未知'}。",
    ]
    if raw.get("fallback_mock"):
        context.append("这次没有拿到可靠 yfinance 数据，报告只能作为行为风控提醒，不能当成基本面研究。")
    elif raw.get("pe") is not None and float(raw.get("pe") or 0) > 80:
        context.append("高 PE 不是不能买，但它要求未来增长持续兑现；一旦预期降温，回撤会比故事来得更快。")
    return context


def build_devil_advocate(asset: str, asset_type: str, risk_scan: dict, emotion_scan: dict, bias_detection: dict) -> dict:
    raw = risk_scan.get("raw_data") or {}
    market_context = _market_context(asset_type, raw)
    against = [
        f"如果我是反方，我会反对你现在买 {asset}，因为当前风险分是 {risk_scan['risk_score']}，这不是低噪音环境。",
        market_context[0],
        "你的最大风险不是这个资产会不会跌，而是你没有想过它跌了以后怎么办。",
        "如果你说不出失效条件，这不是投资，这是情绪下注。",
        "市场不会因为你害怕错过就给你更好的买点。冲动买入通常把风控放在最后。",
    ]
    against.extend(market_context[1:])

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
