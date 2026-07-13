def make_decision(
    risk_score: int,
    emotion_score: int,
    bias_score: int,
    conviction_score: int,
    kol_dependency: int = 0,
    kol_triggered: bool = False,
    data_confidence_score: int | None = None,
    trade_direction: str = "long",
    historical_risk_adjustment: int = 0,
    historical_patterns: list[str] | None = None,
) -> dict:
    is_short = trade_direction == "short"
    is_watch = trade_direction == "watch"
    block_label = "🔴 Don't Short" if is_short else "🔴 Don't Buy"
    small_label = "🟢 Small Short" if is_short else "🟢 Small Position"
    action_word = "做空" if is_short else "买入"
    reasons = []
    historical_patterns = historical_patterns or []
    if is_watch:
        reasons.append("你选择的是观望，系统会帮你检查是否有必要现在开仓")
        decision = "🟡 Wait"
    elif historical_risk_adjustment >= 25:
        reasons.append("这次输入重复了多个历史高危行为模式，先不要让旧习惯再次接管决策")
        decision = block_label
    elif is_short and risk_score >= 70:
        reasons.append(f"资产风险分 {risk_score} 偏高，但做空不是风控，波动和逼空会放大亏损")
        decision = block_label
    elif data_confidence_score is not None and data_confidence_score < 25:
        reasons.append(f"数据置信度只有 {data_confidence_score}，当前信息不足以支持{action_word}")
        decision = block_label
    elif kol_triggered and emotion_score > 70:
        reasons.append(f"这次{action_word}同时触发 KOL 驱动和高情绪风险")
        decision = block_label
    elif risk_score >= 80:
        reasons.append(f"资产风险分 {risk_score} 已进入极高风险区间")
        decision = block_label
    elif emotion_score >= 80:
        reasons.append(f"情绪分 {emotion_score} 说明你现在高度冲动")
        decision = block_label
    elif bias_score >= 80:
        reasons.append(f"认知偏差分 {bias_score}，你正在被叙事牵着走")
        decision = block_label
    elif conviction_score <= 40:
        reasons.append(f"信念分 {conviction_score} 太低，{action_word}逻辑撑不起风险")
        decision = block_label
    elif kol_dependency > 80 and conviction_score < 50:
        reasons.append("你的 KOL Dependency 很高，但独立信念不足，至少先等待")
        decision = "🟡 Wait"
    elif data_confidence_score is not None and data_confidence_score < 45:
        reasons.append(f"数据置信度 {data_confidence_score} 偏低，不能把当前报告当作完整研究")
        decision = "🟡 Wait"
    elif historical_risk_adjustment >= 10 and conviction_score < 75:
        reasons.append("历史 DNA 显示这次可能在重复旧模式，先等待并补全计划")
        decision = "🟡 Wait"
    elif risk_score >= 60 or emotion_score >= 60 or bias_score >= 60:
        reasons.append("风险、情绪或偏差至少一项进入高压区，先等情绪降温")
        decision = "🟡 Wait"
    elif conviction_score >= 75 and risk_score < 60 and emotion_score < 60:
        reasons.append("信念结构较完整，且风险和情绪未进入高压区")
        decision = small_label
    else:
        reasons.append("证据还不够硬，等待比冲动下单更值钱")
        decision = "🟡 Wait"

    if historical_patterns:
        reasons.append(f"历史重复模式：{'、'.join(historical_patterns[:2])}")

    if decision.startswith("🔴 Don't"):
        position = "不建议做空，至少等待 24 小时后重新评估，并确认最大亏损规则。" if is_short else "不建议买入，至少等待 24 小时后重新评估。"
    elif decision == "🟡 Wait":
        position = "建议观察，暂时不需要开仓。" if is_watch else "建议观察，不超过 5% 试错仓位。"
    else:
        position = "只允许小仓位做空，必须设置止损，建议风险敞口不超过总资金 3%-5%。" if is_short else "只允许小仓位，建议不超过总资金 5%-10%。"

    return {
        "final_decision": decision,
        "decision_reason": "；".join(reasons),
        "position_advice": position,
    }
