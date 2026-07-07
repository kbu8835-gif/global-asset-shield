def make_decision(
    risk_score: int,
    emotion_score: int,
    bias_score: int,
    conviction_score: int,
    kol_dependency: int = 0,
    kol_triggered: bool = False,
    data_confidence_score: int | None = None,
) -> dict:
    reasons = []
    if data_confidence_score is not None and data_confidence_score < 25:
        reasons.append(f"数据置信度只有 {data_confidence_score}，当前信息不足以支持买入")
        decision = "🔴 Don't Buy"
    elif kol_triggered and emotion_score > 70:
        reasons.append("这次买入同时触发 KOL 驱动和高情绪风险")
        decision = "🔴 Don't Buy"
    elif risk_score >= 80:
        reasons.append(f"资产风险分 {risk_score} 已进入极高风险区间")
        decision = "🔴 Don't Buy"
    elif emotion_score >= 80:
        reasons.append(f"情绪分 {emotion_score} 说明你现在高度冲动")
        decision = "🔴 Don't Buy"
    elif bias_score >= 80:
        reasons.append(f"认知偏差分 {bias_score}，你正在被叙事牵着走")
        decision = "🔴 Don't Buy"
    elif conviction_score <= 40:
        reasons.append(f"信念分 {conviction_score} 太低，买入逻辑撑不起风险")
        decision = "🔴 Don't Buy"
    elif kol_dependency > 80 and conviction_score < 50:
        reasons.append("你的 KOL Dependency 很高，但独立信念不足，至少先等待")
        decision = "🟡 Wait"
    elif data_confidence_score is not None and data_confidence_score < 45:
        reasons.append(f"数据置信度 {data_confidence_score} 偏低，不能把当前报告当作完整研究")
        decision = "🟡 Wait"
    elif risk_score >= 60 or emotion_score >= 60 or bias_score >= 60:
        reasons.append("风险、情绪或偏差至少一项进入高压区，先等情绪降温")
        decision = "🟡 Wait"
    elif conviction_score >= 75 and risk_score < 60 and emotion_score < 60:
        reasons.append("信念结构较完整，且风险和情绪未进入高压区")
        decision = "🟢 Small Position"
    else:
        reasons.append("证据还不够硬，等待比冲动下单更值钱")
        decision = "🟡 Wait"

    if decision == "🔴 Don't Buy":
        position = "不建议买入，至少等待 24 小时后重新评估。"
    elif decision == "🟡 Wait":
        position = "建议观察，不超过 5% 试错仓位。"
    else:
        position = "只允许小仓位，建议不超过总资金 5%-10%。"

    return {
        "final_decision": decision,
        "decision_reason": "；".join(reasons),
        "position_advice": position,
    }
