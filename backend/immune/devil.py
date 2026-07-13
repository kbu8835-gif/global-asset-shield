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


def build_devil_advocate(
    asset: str,
    asset_type: str,
    risk_scan: dict,
    emotion_scan: dict,
    bias_detection: dict,
    trade_direction: str = "long",
    payload=None,
    data_confidence: dict | None = None,
) -> dict:
    raw = risk_scan.get("raw_data") or {}
    market_context = _market_context(asset_type, raw)
    buy_reason = getattr(payload, "buy_reason", None) or ""
    position_size = getattr(payload, "position_size", None) or ""
    risk_awareness = getattr(payload, "risk_awareness", None) or ""
    favorable_plan = getattr(payload, "favorable_plan", None) or ""
    sideways_plan = getattr(payload, "sideways_plan", None) or ""
    worst_case_plan = getattr(payload, "worst_case_plan", None) or ""
    user_intent = getattr(payload, "user_intent", None) or ""
    confidence_score = int((data_confidence or {}).get("score") or 0)

    plan_line = ""
    if favorable_plan or sideways_plan or worst_case_plan:
        if trade_direction == "short":
            plan_line = f"你写的计划是：跌了“{favorable_plan or '未写'}”，横盘“{sideways_plan or '未写'}”，涨了“{worst_case_plan or '未写'}”。反方会检查你是否真的执行，而不是临场改口。"
        else:
            plan_line = f"你写的计划是：涨了“{favorable_plan or '未写'}”，横盘“{sideways_plan or '未写'}”，跌了“{worst_case_plan or '未写'}”。反方会检查这是不是规则，还是安慰自己的句子。"

    size_line = ""
    if position_size:
        size_line = f"你准备投入 {position_size}。仓位越大，判断正确也可能因为波动被迫犯错。"

    reason_line = ""
    if buy_reason:
        reason_line = f"你的理由是“{buy_reason}”。反方要问：这是可验证证据，还是一句情绪叙事？"

    confidence_line = ""
    if confidence_score and confidence_score < 50:
        confidence_line = f"这次数据置信度只有 {confidence_score}，反方不会允许你把低置信数据当成高确定性结论。"

    if trade_direction == "short":
        against = [
            f"如果我是反方，我会反对你现在做空 {asset}，因为当前风险分是 {risk_scan['risk_score']}，波动本身就能先打爆没有规则的空头。",
            market_context[0],
            "做空的风险不是只会亏本金。逼空、跳空和资金费率会让你在方向看对前先被迫出局。",
            reason_line or "你需要证明自己有下跌逻辑、入场时机和止损规则，而不是只是在表达讨厌这个资产。",
            plan_line or "如果你说不出被逼空时怎么退出，这不是风控，这是反向情绪下注。",
        ]
    elif trade_direction == "watch":
        against = [
            f"如果我是反方，我会反对你现在开仓 {asset}，因为观望本身已经说明证据还不够硬。",
            market_context[0],
            reason_line or "你现在真正要做的不是找一个方向，而是确认哪些数据会让你改变判断。",
            "没有触发条件的观察，最后很容易变成临场追单。",
            plan_line or "如果你说不出下一次复查时间，观望也会变成拖延式下注。",
        ]
    else:
        against = [
            f"如果我是反方，我会反对你现在买 {asset}，因为当前风险分是 {risk_scan['risk_score']}，这不是低噪音环境。",
            market_context[0],
            reason_line or "你的最大风险不是这个资产会不会跌，而是你没有想过它跌了以后怎么办。",
            plan_line or "如果你说不出失效条件，这不是投资，这是情绪下注。",
            "市场不会因为你害怕错过就给你更好的买点。冲动买入通常把风控放在最后。",
        ]
    for optional in [size_line, confidence_line]:
        if optional:
            against.append(optional)
    against.extend(market_context[1:])

    bias_types = {item["bias_type"] for item in bias_detection.get("biases", [])}
    if "FOMO" in bias_types or "FOMO" in emotion_scan.get("detected_emotions", []):
        against.append("你现在可能不是在研究机会，而是在逃避错过的焦虑。")
    if any(word in f"{user_intent} {buy_reason}" for word in ["KOL", "朋友", "群里", "博主", "老师"]):
        against.append("这次输入有外部观点驱动。反方不会否定别人观点，但会否定你把别人观点当成自己的交易计划。")
    if asset_type == "crypto":
        against.append("Crypto 的流动性可以在你想卖时消失，盘口深度比叙事更诚实。")
    else:
        against.append("热门股票的好公司和好买点不是一回事，估值过热时也会伤人。")

    if trade_direction == "short":
        supporting = [
            f"支持做空的理由可能是：{buy_reason or '你有清楚的下跌逻辑'}，并且能被事实证伪。",
            f"支持做空的理由可能是：仓位是 {position_size or '小仓位'}，即使被逼空也不会伤到本金结构。",
        ]
        killer = [
            f"如果先涨到你的认错线，你会按“{worst_case_plan or '预设止损'}”执行，还是重新找理由？",
            "你的做空逻辑是基本面恶化、估值过热，还是单纯觉得它涨多了？",
            "谁可能在继续买入推高价格，为什么你确定他会停？",
            f"如果横盘到“{sideways_plan or '你设定的期限'}”，你会退出还是继续耗着？",
        ]
    elif trade_direction == "watch":
        supporting = [
            "支持继续观望的理由可能是：你已经列出下一次复查的触发条件。",
            "支持继续观望的理由可能是：当前数据置信度不够，等待能减少错误下注。",
        ]
        killer = [
            "什么信号出现后，你才会考虑开仓？",
            "如果它上涨但没有达到你的条件，你能不能忍住不追？",
            "你下一次复查的具体时间是什么？",
        ]
    else:
        supporting = [
            f"支持买入的理由可能是：{buy_reason or '你有独立研究'}，并且能写出明确失效条件。",
            f"支持买入的理由可能是：仓位是 {position_size or '小仓位'}，错了也不会影响长期本金。",
        ]

        killer = [
            f"如果先跌到你的退出线，你会按“{worst_case_plan or '预设止损'}”执行，还是临场改规则？",
            "谁可能正在把筹码卖给你，为什么他愿意卖？",
            "什么事实出现后，你会承认自己错了？",
            f"如果横盘到“{sideways_plan or '你设定的期限'}”，你会继续等还是为了有动作而加仓？",
        ]

    return {
        "against_buying": against[:6],
        "supporting_case": supporting,
        "killer_questions": killer,
    }
