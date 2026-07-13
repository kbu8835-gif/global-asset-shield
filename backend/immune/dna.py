from typing import Dict, List, Optional, Tuple

from immune.decision_record import DecisionRecord, list_decision_records
from immune.kol_intelligence import calculate_user_kol_dependency
from scanner.utils import clamp_score
from schemas import DNAEvidenceGroup, DNAEvidenceRecord, InvestmentDNAResponse


FOMO_WORDS = ["FOMO", "Fear", "涨很多", "怕踏空", "错过", "起飞", "再不上车"]
KOL_WORDS = ["KOL", "kol", "大V", "博主", "喊单", "老师说", "群里说", "KOL推荐"]
ALL_IN_WORDS = ["满仓", "梭哈", "重仓", "50%", "80%", "全部", "all in"]
NO_STOP_WORDS = ["跌了就再看看", "再看看", "不清楚", "不知道", "没想过", "没有止损", "没止损"]


def _has_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def _first_match(text: str, words: List[str]) -> Optional[str]:
    return next((word for word in words if word in text), None)


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def _average(entries: List[DecisionRecord], field: str, default: int = 0) -> int:
    values = [int(getattr(entry, field, 0) or 0) for entry in entries]
    if not values:
        return default
    return int(sum(values) / len(values))


def _investor_type(fomo_rate: float, kol_rate: float, all_in_rate: float, avg_conviction: int) -> str:
    if fomo_rate > 0.4:
        return "FOMO Hunter"
    if kol_rate > 0.4:
        return "Narrative Chaser"
    if all_in_rate > 0.4:
        return "High Roller"
    if avg_conviction < 30:
        return "Weak Conviction"
    return "Balanced Investor"


def _field_texts(entry: DecisionRecord) -> List[Tuple[str, str]]:
    return [
        ("用户意图", entry.user_intent),
        ("用户原文", entry.user_text),
        ("买入/做空理由", entry.buy_reason),
        ("仓位", entry.position_size),
        ("风险意识", entry.risk_awareness),
        ("最坏情况计划", entry.worst_case_plan),
        ("Notebook 记录", entry.notes),
        ("用户最终决定", entry.user_decision),
        ("复盘原文", entry.review_result_text),
        ("复盘识别结果", entry.review_outcome_label),
        ("复盘错误类型", entry.mistakes),
        ("复盘教训", entry.lesson),
        ("下一条规则", entry.next_action),
    ]


def _system_field_texts(entry: DecisionRecord) -> List[Tuple[str, str]]:
    return [
        ("AI 建议", entry.ai_decision),
        ("用户最终决定", entry.user_decision),
        ("报告摘要", entry.summary),
    ]


def _excerpt(text: str, keyword: str) -> str:
    if not text:
        return ""
    index = text.find(keyword)
    if index < 0:
        return text[:90]
    start = max(0, index - 28)
    end = min(len(text), index + len(keyword) + 42)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _record_evidence(entry: DecisionRecord, field: str, keyword: str, text: str) -> DNAEvidenceRecord:
    return DNAEvidenceRecord(
        record_id=entry.id,
        source=entry.source,
        asset=entry.asset,
        asset_type=entry.asset_type,
        trade_direction=entry.trade_direction,
        created_at=entry.created_at,
        field=field,
        keyword=keyword,
        excerpt=_excerpt(text, keyword),
    )


def _collect_user_evidence(entries: List[DecisionRecord], words: List[str], limit: int = 5) -> List[DNAEvidenceRecord]:
    evidence: List[DNAEvidenceRecord] = []
    seen = set()
    for entry in entries:
        for field, text in _field_texts(entry):
            keyword = _first_match(text, words)
            if not keyword:
                continue
            key = (entry.source, entry.id, field, keyword)
            if key in seen:
                continue
            evidence.append(_record_evidence(entry, field, keyword, text))
            seen.add(key)
            break
        if len(evidence) >= limit:
            break
    return evidence


def _collect_system_evidence(entries: List[DecisionRecord], words: List[str], limit: int = 5) -> List[DNAEvidenceRecord]:
    evidence: List[DNAEvidenceRecord] = []
    seen = set()
    for entry in entries:
        for field, text in _system_field_texts(entry):
            keyword = _first_match(text, words)
            if not keyword:
                continue
            key = (entry.source, entry.id, field, keyword)
            if key in seen:
                continue
            evidence.append(_record_evidence(entry, field, keyword, text))
            seen.add(key)
            break
        if len(evidence) >= limit:
            break
    return evidence


def _score_evidence(entries: List[DecisionRecord], limit: int = 5) -> List[DNAEvidenceRecord]:
    scored = sorted(entries, key=lambda entry: (entry.risk_score + entry.emotion_score + entry.bias_score - entry.conviction_score), reverse=True)
    evidence: List[DNAEvidenceRecord] = []
    for entry in scored[:limit]:
        text = (
            f"Risk {entry.risk_score}, Emotion {entry.emotion_score}, Bias {entry.bias_score}, "
            f"Conviction {entry.conviction_score}"
        )
        evidence.append(_record_evidence(entry, "评分来源", "scores", text))
    return evidence


def _review_evidence(entries: List[DecisionRecord], limit: int = 5) -> List[DNAEvidenceRecord]:
    evidence: List[DNAEvidenceRecord] = []
    for entry in entries:
        if not entry.was_reviewed:
            continue
        text = entry.review_result_text or entry.review_outcome_label or entry.mistakes or entry.lesson
        keyword = entry.review_outcome_label or entry.mistakes or "reviewed"
        evidence.append(_record_evidence(entry, "复盘结果", keyword, text))
        if len(evidence) >= limit:
            break
    return evidence


def _build_evidence_sources(
    entries: List[DecisionRecord],
    counts: Dict[str, int],
    total: int,
) -> List[DNAEvidenceGroup]:
    return [
        DNAEvidenceGroup(
            signal="FOMO / 追涨",
            explanation="用于判断 Patience、Emotion Control 和投资者类型。只读取用户输入与 Notebook 内容。",
            count=counts["fomo"],
            records=_collect_user_evidence(entries, FOMO_WORDS),
        ),
        DNAEvidenceGroup(
            signal="KOL / 外部观点",
            explanation="用于判断 KOL Dependency 和 Independent Thinking。系统模板里的 KOL 提醒不会被计入。",
            count=counts["kol"],
            records=_collect_user_evidence(entries, KOL_WORDS),
        ),
        DNAEvidenceGroup(
            signal="高仓位 / All-in",
            explanation="用于判断 Discipline 和 Risk Appetite。",
            count=counts["all_in"],
            records=_collect_user_evidence(entries, ALL_IN_WORDS),
        ),
        DNAEvidenceGroup(
            signal="退出计划不清晰",
            explanation="用于判断 Discipline。证据来自风险意识、最坏情况计划和用户笔记。",
            count=counts["no_stop"],
            records=_collect_user_evidence(entries, NO_STOP_WORDS),
        ),
        DNAEvidenceGroup(
            signal="AI 阻止过的交易",
            explanation="用于显示系统曾经给出 Don't Buy / Don't Short 的记录。",
            count=counts["dont_buy"],
            records=_collect_system_evidence(entries, ["Don't Buy", "Don't Short", "不建议买入", "不建议做空"]),
        ),
        DNAEvidenceGroup(
            signal="复盘结果回流",
            explanation="用于判断 Discipline、Research 和后续规则是否真正被写入。只有提交过复盘的记录才会出现在这里。",
            count=counts["reviewed"],
            records=_review_evidence(entries),
        ),
        DNAEvidenceGroup(
            signal="评分来源样本",
            explanation=f"用于计算长期指标的最近{total}条记录评分样本，优先显示综合风险更高的记录。",
            count=total,
            records=_score_evidence(entries),
        ),
    ]


def build_investment_dna(user_id: int) -> InvestmentDNAResponse:
    entries = list_decision_records(user_id)
    total = len(entries)
    if total == 0:
        return InvestmentDNAResponse(
            investor_type="Balanced Investor",
            discipline=100,
            patience=100,
            risk_appetite=0,
            kol_dependency=0,
            conviction=0,
            emotion_control=100,
            independent_thinking=100,
            summary="还没有投资日记。AI 需要至少一次免疫扫描，才能发现你的行为重复模式。",
            kol_summary="还没有足够记录判断是否出现 KOL/外部观点相关线索。",
            top_kol_influences=[],
            evidence_window="最近0条",
            evidence_sources=[],
        )

    texts = [entry.user_decision_text for entry in entries]
    system_texts = [entry.system_decision_text for entry in entries]
    fomo_count = sum(_has_any(text, FOMO_WORDS) for text in texts)
    kol_count = sum(_has_any(text, KOL_WORDS) for text in texts)
    all_in_count = sum(_has_any(text, ALL_IN_WORDS) for text in texts)
    no_stop_count = sum(_has_any(text, NO_STOP_WORDS) for text in texts)
    reviewed_count = sum(1 for entry in entries if entry.was_reviewed)
    dont_buy_count = sum(
        "Don't Buy" in text
        or "Don't Short" in text
        or "不建议买入" in text
        or "不建议做空" in text
        for text in system_texts
    )
    counts = {
        "fomo": fomo_count,
        "kol": kol_count,
        "all_in": all_in_count,
        "no_stop": no_stop_count,
        "dont_buy": dont_buy_count,
        "reviewed": reviewed_count,
    }

    avg_emotion = _average(entries, "emotion_score")
    avg_bias = _average(entries, "bias_score")
    avg_conviction = _average(entries, "conviction_score")
    avg_risk = _average(entries, "risk_score")

    fomo_rate = _rate(fomo_count, total)
    kol_rate = _rate(kol_count, total)
    all_in_rate = _rate(all_in_count, total)
    no_stop_rate = _rate(no_stop_count, total)
    dont_buy_rate = _rate(dont_buy_count, total)

    discipline = clamp_score(100 - int(all_in_rate * 35) - int(no_stop_rate * 35) - int(avg_bias * 0.25))
    discipline = clamp_score(discipline + min(reviewed_count * 6, 24))
    patience = clamp_score(100 - int(fomo_rate * 45) - int(avg_emotion * 0.35) - int(all_in_rate * 20))
    patience = clamp_score(patience + min(reviewed_count * 3, 12))
    risk_appetite = clamp_score(int(avg_risk * 0.45) + int(all_in_rate * 35) + int(fomo_rate * 25))
    emotion_control = clamp_score(100 - int(avg_emotion * 0.65) - int(fomo_rate * 25))
    kol_dependency_data = calculate_user_kol_dependency(user_id)
    kol_dependency = max(clamp_score(int(kol_rate * 100)), kol_dependency_data.kol_dependency)
    independent_thinking = clamp_score(100 - int(kol_rate * 55) - int(avg_bias * 0.2))
    if kol_dependency > 70:
        independent_thinking = clamp_score(independent_thinking - 20)
    conviction = clamp_score(avg_conviction)
    if reviewed_count:
        conviction = clamp_score(conviction + min(reviewed_count * 4, 16))

    investor_type = _investor_type(fomo_rate, kol_rate, all_in_rate, avg_conviction)
    window = "最近50条" if total == 50 else f"最近{total}条"
    summary = (
        f"{window}投资日记里，AI只根据你写下的内容做行为线索统计："
        f"FOMO/追涨相关表达{fomo_count}次，KOL/他人观点相关表达{kol_count}次，"
        f"高仓位表达{all_in_count}次，退出计划不清晰表达{no_stop_count}次，"
        f"系统给出 Don't Buy/Don't Short 建议{dont_buy_count}次，"
        f"已完成复盘{reviewed_count}次。"
    )
    has_kol_evidence = kol_count > 0 or kol_dependency_data.kol_related_count > 0
    if has_kol_evidence:
        summary += "这不等于你一定在盲从，但说明记录里出现了外部观点线索；请确认它只是信息来源，而不是替代你的交易计划。"
    else:
        summary += "目前没有从用户输入中发现明显 KOL 依赖表达，重点仍是检查情绪升温时能否执行自己的交易规则。"
    if has_kol_evidence and kol_dependency > 80:
        summary += "如果这些 KOL/外部观点线索不是你的真实决策依据，可以回到笔记本修改原始记录，DNA 会随记录更新。"

    return InvestmentDNAResponse(
        investor_type=investor_type,
        discipline=discipline,
        patience=patience,
        risk_appetite=risk_appetite,
        kol_dependency=kol_dependency,
        conviction=conviction,
        emotion_control=emotion_control,
        independent_thinking=independent_thinking,
        summary=summary,
        kol_summary=kol_dependency_data.summary,
        top_kol_influences=kol_dependency_data.top_kol_names,
        evidence_window=window,
        evidence_sources=_build_evidence_sources(entries, counts, total),
    )
