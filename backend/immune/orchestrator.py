from immune.bias import detect_bias
from immune.conviction import build_conviction_score
from immune.data_confidence import build_data_confidence
from immune.decision import make_decision
from immune.devil import build_devil_advocate
from immune.direction import direction_label, normalize_trade_direction
from immune.emotion import scan_emotion
from immune.history import build_historical_dna_scan
from immune.journal import save_report
from immune.kol_intelligence import build_kol_risk_summary, calculate_user_kol_dependency
from immune.llm import build_ai_coach
from immune.munger import build_munger_lens
from immune.okx_ai_result import build_okx_ai_agent_result
from immune.regret import simulate_regret
from immune.risk import run_risk_scan
from immune.watch import build_observation_plan
from schemas import ImmuneReportRequest, ImmuneReportResponse


def _combined_text(payload: ImmuneReportRequest) -> str:
    return " ".join(
        [
            payload.user_intent or "",
            payload.user_text or "",
            payload.buy_reason or "",
            payload.risk_awareness or "",
            payload.favorable_plan or "",
            payload.sideways_plan or "",
            payload.worst_case_plan or "",
            payload.position_size or "",
            payload.horizon or "",
            payload.trade_direction or "",
        ]
    )


def build_immune_report(payload: ImmuneReportRequest, user_id: int) -> ImmuneReportResponse:
    asset = payload.asset.upper()
    trade_direction = normalize_trade_direction(payload.trade_direction)
    risk_scan = run_risk_scan(payload)
    data_confidence = build_data_confidence(payload.asset_type, risk_scan)
    emotion_scan = scan_emotion(payload)
    bias_detection = detect_bias(_combined_text(payload))
    kol_risk_scan = build_kol_risk_summary(_combined_text(payload), user_id)
    kol_dependency = calculate_user_kol_dependency(user_id).kol_dependency if kol_risk_scan else 0
    historical_dna_scan = build_historical_dna_scan(payload, user_id)
    devil = build_devil_advocate(
        asset,
        payload.asset_type,
        risk_scan,
        emotion_scan,
        bias_detection,
        trade_direction,
        payload=payload,
        data_confidence=data_confidence,
    )
    regret = simulate_regret(asset, emotion_scan["emotion_score"], bias_detection, payload.position_size, trade_direction, payload=payload)
    conviction = build_conviction_score(payload)
    munger_lens = build_munger_lens(payload, risk_scan, emotion_scan, bias_detection, conviction, kol_risk_scan)
    observation_plan = build_observation_plan(payload, asset) if trade_direction == "watch" else None
    decision = make_decision(
        risk_scan["risk_score"],
        emotion_scan["emotion_score"],
        bias_detection["bias_score"],
        conviction["score"],
        kol_dependency=kol_dependency,
        kol_triggered=bool(kol_risk_scan),
        data_confidence_score=data_confidence["score"],
        trade_direction=trade_direction,
        historical_risk_adjustment=historical_dna_scan["risk_adjustment"],
        historical_patterns=historical_dna_scan["triggered_patterns"],
    )
    summary = (
        f"{asset} 本次{direction_label(trade_direction)}免疫扫描：资产风险 {risk_scan['risk_score']}，情绪风险 "
        f"{emotion_scan['emotion_score']}，偏差风险 {bias_detection['bias_score']}，信念分 "
        f"{conviction['score']}。{historical_dna_scan['summary']}。{decision['decision_reason']}。"
    )

    report = {
        "report_id": 0,
        "asset": asset,
        "asset_type": payload.asset_type,
        "trade_direction": trade_direction,
        "risk_scan": risk_scan,
        "data_confidence": data_confidence,
        "emotion_scan": emotion_scan,
        "bias_detection": bias_detection,
        "devil_advocate": devil,
        "regret_simulation": regret,
        "conviction_score": conviction,
        "munger_lens": munger_lens,
        "observation_plan": observation_plan,
        "historical_dna_scan": historical_dna_scan,
        "final_decision": decision["final_decision"],
        "decision_reason": decision["decision_reason"],
        "position_advice": decision["position_advice"],
        "journal_saved": False,
        "summary": summary,
        "kol_risk_scan": kol_risk_scan,
    }
    report["ai_coach"] = build_ai_coach(payload, report, user_id)
    report["okx_ai_agent_result"] = build_okx_ai_agent_result(payload, report)

    report_id = save_report(payload, report, user_id)
    report["report_id"] = report_id
    report["journal_saved"] = True
    return ImmuneReportResponse(**report)
