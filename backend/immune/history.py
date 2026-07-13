from typing import Any, Dict, List

from immune.dna import build_investment_dna
from schemas import ImmuneReportRequest


FOMO_TERMS = ["怕踏空", "错过", "涨很多", "起飞", "再不上车", "FOMO"]
KOL_TERMS = ["KOL", "kol", "大V", "博主", "老师", "群里", "喊单", "朋友推荐"]
SIZE_TERMS = ["50%", "80%", "100%", "满仓", "梭哈", "重仓", "全部", "ALL IN", "all in"]
NO_PLAN_TERMS = ["不清楚", "不知道", "再看看", "没想过", "没有止损", "没止损"]


def _combined_text(payload: ImmuneReportRequest) -> str:
    return " ".join(
        [
            payload.user_intent or "",
            payload.user_text or "",
            payload.buy_reason or "",
            payload.risk_awareness or "",
            payload.worst_case_plan or "",
            payload.position_size or "",
            payload.horizon or "",
        ]
    )


def _has_any(text: str, terms: List[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _top_evidence(dna: Any, signals: List[str], limit: int = 4) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for group in getattr(dna, "evidence_sources", []) or []:
        if group.signal not in signals:
            continue
        for record in group.records:
            evidence.append(
                {
                    "signal": group.signal,
                    "record_id": record.record_id,
                    "asset": record.asset,
                    "field": record.field,
                    "keyword": record.keyword,
                    "excerpt": record.excerpt,
                    "created_at": record.created_at,
                }
            )
            if len(evidence) >= limit:
                return evidence
    return evidence


def build_historical_dna_scan(payload: ImmuneReportRequest, user_id: int) -> Dict[str, Any]:
    dna = build_investment_dna(user_id)
    text = _combined_text(payload)
    triggered_patterns: List[str] = []
    warnings: List[str] = []

    current_fomo = _has_any(text, FOMO_TERMS)
    current_kol = _has_any(text, KOL_TERMS)
    current_size = _has_any(text, SIZE_TERMS)
    current_no_plan = _has_any(text, NO_PLAN_TERMS)

    if current_fomo and (dna.investor_type == "FOMO Hunter" or dna.patience < 45 or dna.emotion_control < 45):
        triggered_patterns.append("历史 FOMO / 本次再次怕错过")
        warnings.append("这次输入再次触发怕错过信号，而你的历史 DNA 显示耐心或情绪控制偏弱。先冷却，不要让上涨替你做决定。")
    if current_kol and (dna.kol_dependency > 50 or dna.independent_thinking < 50):
        triggered_patterns.append("历史外部观点依赖 / 本次再次提到 KOL 或他人观点")
        warnings.append("这次输入出现外部观点线索。别人的观点可以参考，但不能替你承担亏损。")
    if current_size and (dna.discipline < 60 or dna.risk_appetite > 65):
        triggered_patterns.append("历史纪律偏弱 / 本次仓位偏激进")
        warnings.append("这次仓位表达偏激进，而你的历史 DNA 不支持用大仓位试错。先把仓位上限写死。")
    if current_no_plan and dna.discipline < 65:
        triggered_patterns.append("历史退出计划不清 / 本次仍未写清楚最坏情况")
        warnings.append("你这次仍没有写清楚亏损时怎么办。没有退出条件，扫描结果再聪明也救不了执行。")

    if not triggered_patterns:
        warnings.append("这次输入没有明显重复历史高危模式。继续保持：先写计划，再谈开仓。")

    risk_adjustment = 0
    if current_fomo and dna.emotion_control < 45:
        risk_adjustment += 10
    if current_kol and dna.kol_dependency > 70:
        risk_adjustment += 10
    if current_size and dna.discipline < 50:
        risk_adjustment += 10
    if current_no_plan and dna.discipline < 50:
        risk_adjustment += 10

    signals = ["FOMO / 追涨", "KOL / 外部观点", "高仓位 / All-in", "退出计划不清晰", "复盘结果回流"]
    summary = (
        f"历史 DNA：{dna.investor_type}。纪律 {dna.discipline}，耐心 {dna.patience}，"
        f"情绪控制 {dna.emotion_control}，独立思考 {dna.independent_thinking}。"
        f"本次命中 {len(triggered_patterns)} 个历史重复模式。"
    )

    return {
        "available": True,
        "investor_type": dna.investor_type,
        "discipline": dna.discipline,
        "patience": dna.patience,
        "risk_appetite": dna.risk_appetite,
        "kol_dependency": dna.kol_dependency,
        "emotion_control": dna.emotion_control,
        "independent_thinking": dna.independent_thinking,
        "triggered_patterns": triggered_patterns,
        "warnings": warnings,
        "risk_adjustment": risk_adjustment,
        "evidence": _top_evidence(dna, signals),
        "summary": summary,
    }
