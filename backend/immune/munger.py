from schemas import ImmuneReportRequest


def _bias_types(bias_detection: dict) -> set[str]:
    return {item.get("bias_type", "") for item in bias_detection.get("biases", []) if isinstance(item, dict)}


def _has_kol(payload: ImmuneReportRequest, kol_risk_scan: dict | None) -> bool:
    text = " ".join(
        [
            payload.user_intent or "",
            payload.user_text or "",
            payload.buy_reason or "",
        ]
    ).lower()
    return bool(kol_risk_scan) or any(word in text for word in ["kol", "大v", "博主", "老师", "喊单", "群里"])


def _position_is_large(position_size: str | None) -> bool:
    text = (position_size or "").lower()
    return any(word in text for word in ["50%", "80%", "全部", "all", "满仓", "梭哈"])


def build_munger_lens(
    payload: ImmuneReportRequest,
    risk_scan: dict,
    emotion_scan: dict,
    bias_detection: dict,
    conviction: dict,
    kol_risk_scan: dict | None = None,
) -> dict:
    asset = payload.asset.upper()
    biases = _bias_types(bias_detection)
    raw = risk_scan.get("raw_data") or {}
    risk_score = int(risk_scan.get("risk_score") or 0)
    conviction_score = int(conviction.get("score") or 0)
    emotion_score = int(emotion_scan.get("emotion_score") or 0)

    failure_paths = [
        "你买入后没有预先写下卖出条件，价格一跌就开始临场编理由。",
        "你把上涨、KOL 和群体兴奋误认为安全边际。",
    ]
    if risk_score >= 60:
        failure_paths.append(f"{asset} 的资产风险分已经到 {risk_score}，你仍然用短线情绪做长期伤害。")
    if _position_is_large(payload.position_size):
        failure_paths.append("仓位过大让一次错误判断变成系统性损伤。")
    if raw.get("fallback_mock"):
        failure_paths.append("这次没有拿到可靠外部行情，你在信息不完整时想做决定。")

    incentive_check = "先问谁在赚钱，谁在承担风险。"
    if _has_kol(payload, kol_risk_scan):
        incentive_check = "KOL 赚的是注意力和影响力，亏损由你承担。激励不对齐时，别把他的观点当成你的买入理由。"

    lollapalooza = []
    if "FOMO" in biases or "FOMO" in emotion_scan.get("detected_emotions", []):
        lollapalooza.append("社会认同 + 被剥夺反应：别人好像都上车了，你害怕自己被落下。")
    if "Authority Bias" in biases or _has_kol(payload, kol_risk_scan):
        lollapalooza.append("权威偏误：你把别人的确信感借来当自己的研究。")
    if "Lottery Bias" in biases:
        lollapalooza.append("彩票心理：你在用小概率暴富故事覆盖普通情形。")
    if _position_is_large(payload.position_size):
        lollapalooza.append("仓位冲动：你不是在提高胜率，而是在放大后果。")
    if not lollapalooza:
        lollapalooza.append("暂未看到多重偏误同时发力，但仍需要反面证据。")

    if conviction_score <= 40:
        circle = "你还没赚到持有观点的资格。说不清风险、失效条件和仓位逻辑，就不在能力圈内。"
    elif raw.get("fallback_mock"):
        circle = "行情数据不完整，这笔决策至少应该进入 Too Hard，而不是立即下单。"
    else:
        circle = "可以继续研究，但只有你能独立解释资产、风险和退出条件，才算进入能力圈。"

    if risk_score >= 80 or emotion_score >= 80 or conviction_score <= 40:
        verdict = "No"
    elif raw.get("fallback_mock") or risk_score >= 60:
        verdict = "Too Hard"
    else:
        verdict = "Small Bet"

    if verdict == "No":
        one_sentence = "这不是聪明不聪明的问题，这是在避免做一件明显容易变蠢的事。"
    elif verdict == "Too Hard":
        one_sentence = "进 Too Hard 篮子不是怂，是承认自己还没有足够资格下注。"
    else:
        one_sentence = "如果非要做，也只能小到错误不会改变你的生活。"

    return {
        "framework": "Munger Lens",
        "inversion": {
            "question": "如果这笔交易要失败，最可能怎么失败？",
            "failure_paths": failure_paths,
        },
        "circle_of_competence": circle,
        "incentive_check": incentive_check,
        "lollapalooza_effect": lollapalooza,
        "too_hard_pile": risk_score >= 60 or raw.get("fallback_mock") or conviction_score <= 40,
        "margin_of_safety": "安全边际不是一句我看好，而是价格、仓位、退出条件三件事同时保护你。",
        "munger_verdict": verdict,
        "one_sentence": one_sentence,
    }
