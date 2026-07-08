from typing import Any, Dict, List

from database import get_connection, init_db
from immune.kol_intelligence import calculate_user_kol_dependency
from scanner.utils import clamp_score
from schemas import InvestmentDNAResponse


FOMO_WORDS = ["FOMO", "Fear", "涨很多", "怕踏空", "错过", "起飞", "再不上车"]
KOL_WORDS = ["KOL", "kol", "大V", "博主", "喊单", "老师说", "群里说", "KOL推荐"]
ALL_IN_WORDS = ["满仓", "梭哈", "重仓", "50%", "80%", "全部", "all in"]
NO_STOP_WORDS = ["跌了就再看看", "再看看", "不清楚", "不知道", "没想过", "没有止损", "没止损"]


def _recent_entries(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _user_decision_text(entry: Dict[str, Any]) -> str:
    parts = [
        entry.get("asset") or "",
        entry.get("user_intent") or "",
        entry.get("user_text") or "",
        entry.get("buy_reason") or "",
        entry.get("position_size") or "",
        entry.get("risk_awareness") or "",
        entry.get("worst_case_plan") or "",
        entry.get("notes") or "",
        entry.get("title") or "",
        entry.get("decision") or "",
    ]
    return " ".join(parts)


def _system_decision_text(entry: Dict[str, Any]) -> str:
    return " ".join([entry.get("summary") or "", entry.get("final_decision") or "", entry.get("decision") or ""])


def _has_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def _average(entries: List[Dict[str, Any]], field: str, default: int = 0) -> int:
    values = []
    for entry in entries:
        value = entry.get(field)
        if value is not None:
            try:
                values.append(int(value))
            except (TypeError, ValueError):
                continue
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


def build_investment_dna(user_id: int) -> InvestmentDNAResponse:
    entries = _recent_entries(user_id)
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
        )

    texts = [_user_decision_text(entry) for entry in entries]
    system_texts = [_system_decision_text(entry) for entry in entries]
    fomo_count = sum(_has_any(text, FOMO_WORDS) for text in texts)
    kol_count = sum(_has_any(text, KOL_WORDS) for text in texts)
    all_in_count = sum(_has_any(text, ALL_IN_WORDS) for text in texts)
    no_stop_count = sum(_has_any(text, NO_STOP_WORDS) for text in texts)
    dont_buy_count = sum(
        "Don't Buy" in text
        or "Don't Short" in text
        or "不建议买入" in text
        or "不建议做空" in text
        for text in system_texts
    )

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
    patience = clamp_score(100 - int(fomo_rate * 45) - int(avg_emotion * 0.35) - int(all_in_rate * 20))
    risk_appetite = clamp_score(int(avg_risk * 0.45) + int(all_in_rate * 35) + int(fomo_rate * 25))
    emotion_control = clamp_score(100 - int(avg_emotion * 0.65) - int(fomo_rate * 25))
    kol_dependency_data = calculate_user_kol_dependency(user_id)
    kol_dependency = max(clamp_score(int(kol_rate * 100)), kol_dependency_data.kol_dependency)
    independent_thinking = clamp_score(100 - int(kol_rate * 55) - int(avg_bias * 0.2))
    if kol_dependency > 70:
        independent_thinking = clamp_score(independent_thinking - 20)
    conviction = clamp_score(avg_conviction)

    investor_type = _investor_type(fomo_rate, kol_rate, all_in_rate, avg_conviction)
    window = "最近50条" if total == 50 else f"最近{total}条"
    summary = (
        f"{window}投资日记里，AI只根据你写下的内容做行为线索统计："
        f"FOMO/追涨相关表达{fomo_count}次，KOL/他人观点相关表达{kol_count}次，"
        f"高仓位表达{all_in_count}次，退出计划不清晰表达{no_stop_count}次，"
        f"系统给出 Don't Buy/Don't Short 建议{dont_buy_count}次。"
    )
    if kol_count > 0 or kol_dependency > 40:
        summary += "这不等于你一定在盲从，但说明记录里出现了外部观点线索；请确认它只是信息来源，而不是替代你的交易计划。"
    else:
        summary += "目前没有从用户输入中发现明显 KOL 依赖表达，重点仍是检查情绪升温时能否执行自己的交易规则。"
    if kol_dependency > 80:
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
    )
