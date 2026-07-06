import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_connection, init_db
from scanner.crypto import scan_crypto
from scanner.stock import scan_stock
from scanner.utils import clamp_score
from schemas import KOLCall, KOLCallCreate, KOLCallUpdate, KOLDependencyResponse, KOLProfile, KOLProfileCreate, KOLProfileUpdate


KOL_KEYWORDS = ["KOL", "kol", "博主", "大V", "老师", "群里", "朋友推荐", "喊单", "推特", "Twitter", "x.com", "YouTube", "Telegram"]
FOMO_WORDS = ["100x", "10x", "moon", "last chance", "never sell", "暴富", "财富自由", "起飞", "梭哈"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile(row) -> KOLProfile:
    return KOLProfile(**dict(row))


def _call(row) -> KOLCall:
    return KOLCall(**dict(row))


def _risk_level(score: int) -> str:
    if score <= 30:
        return "High Risk KOL"
    if score <= 60:
        return "Mixed Record"
    if score <= 80:
        return "Relatively Reliable"
    return "Strong Record"


def _roi(call_price: Optional[float], current_price: Optional[float]) -> Optional[float]:
    if not call_price or current_price is None:
        return None
    return round(((current_price - call_price) / call_price) * 100, 4)


def extract_kol_signals_from_text(text: str) -> Dict[str, Any]:
    haystack = text or ""
    kol_detected = any(word.lower() in haystack.lower() for word in KOL_KEYWORDS)
    fomo = [word for word in FOMO_WORDS if word.lower() in haystack.lower()]
    return {
        "kol_detected": kol_detected,
        "emotion_tags": ["FOMO"] if fomo else [],
        "bias_tags": ["Authority Bias"] if kol_detected else [],
        "fomo_words": fomo,
    }


def _current_price(asset: str, asset_type: str) -> Optional[float]:
    try:
        scan = scan_crypto(asset) if asset_type == "crypto" else scan_stock(asset)
        raw = scan.raw_data
        value = raw.get("price_usd") or raw.get("price")
        return float(value) if value not in (None, "") else None
    except Exception:
        return None


def calculate_call_performance(data: Dict[str, Any]) -> Dict[str, Any]:
    current_roi = _roi(data.get("call_price"), data.get("current_price"))
    data["current_roi"] = current_roi
    if current_roi is not None and data.get("result_label") in (None, "pending", "unknown"):
        data["result_label"] = "win" if current_roi > 0 else "loss"
    signals = extract_kol_signals_from_text(data.get("call_text") or "")
    data["emotion_tags"] = json.dumps(signals["emotion_tags"], ensure_ascii=False)
    data["bias_tags"] = json.dumps(signals["bias_tags"], ensure_ascii=False)
    return data


def create_kol_profile(payload: KOLProfileCreate, user_id: int) -> KOLProfile:
    init_db()
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kol_profiles (user_id, name, twitter_handle, telegram_handle, youtube_channel, website, bio, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, payload.name, payload.twitter_handle, payload.telegram_handle, payload.youtube_channel, payload.website, payload.bio, now, now),
        )
        conn.commit()
        return get_kol_profile(int(cursor.lastrowid), user_id)


def list_kol_profiles(user_id: int) -> List[KOLProfile]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM kol_profiles WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (user_id,)).fetchall()
    return [_profile(row) for row in rows]


def get_kol_profile(kol_id: int, user_id: int) -> Optional[KOLProfile]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM kol_profiles WHERE id = ? AND user_id = ?", (kol_id, user_id)).fetchone()
    return _profile(row) if row else None


def update_kol_profile(kol_id: int, payload: KOLProfileUpdate, user_id: int) -> Optional[KOLProfile]:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_kol_profile(kol_id, user_id)
    updates["updated_at"] = _now()
    with get_connection() as conn:
        if conn.execute("SELECT id FROM kol_profiles WHERE id = ? AND user_id = ?", (kol_id, user_id)).fetchone() is None:
            return None
        conn.execute(
            f"UPDATE kol_profiles SET {', '.join(f'{key} = ?' for key in updates)} WHERE id = ? AND user_id = ?",
            list(updates.values()) + [kol_id, user_id],
        )
        conn.commit()
    return get_kol_profile(kol_id, user_id)


def delete_kol_profile(kol_id: int, user_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM kol_profiles WHERE id = ? AND user_id = ?", (kol_id, user_id))
        conn.execute("DELETE FROM kol_calls WHERE kol_id = ? AND user_id = ?", (kol_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def create_kol_call(payload: KOLCallCreate, user_id: int) -> KOLCall:
    init_db()
    now = _now()
    data = payload.model_dump()
    if data.get("current_price") is None:
        data["current_price"] = _current_price(data["asset"], data.get("asset_type") or "crypto")
    data = calculate_call_performance(data)
    if data.get("kol_id") and "Authority Bias" not in (data.get("bias_tags") or ""):
        data["bias_tags"] = json.dumps(["Authority Bias"], ensure_ascii=False)
    if data.get("kol_id") and not data.get("kol_name"):
        profile = get_kol_profile(data["kol_id"], user_id)
        data["kol_name"] = profile.name if profile else None
    with get_connection() as conn:
        if data.get("kol_id") and conn.execute("SELECT id FROM kol_profiles WHERE id = ? AND user_id = ?", (data["kol_id"], user_id)).fetchone() is None:
            data["kol_id"] = None
        cursor = conn.execute(
            """
            INSERT INTO kol_calls (
                user_id, kol_id, kol_name, asset, asset_type, call_time, call_price, current_price, source, source_url,
                call_text, call_type, time_horizon, status, roi_7d, roi_30d, current_roi, max_gain,
                max_drawdown, result_label, emotion_tags, bias_tags, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, data.get("kol_id"), data.get("kol_name"), data["asset"], data.get("asset_type") or "crypto",
                data.get("call_time") or now, data.get("call_price"), data.get("current_price"), data.get("source"),
                data.get("source_url"), data.get("call_text"), data.get("call_type"), data.get("time_horizon"),
                data.get("status") or "open", data.get("roi_7d"), data.get("roi_30d"), data.get("current_roi"),
                data.get("max_gain"), data.get("max_drawdown"), data.get("result_label") or "pending",
                data.get("emotion_tags"), data.get("bias_tags"), now, now,
            ),
        )
        conn.commit()
        call = get_kol_call(int(cursor.lastrowid), user_id)
    if call and call.kol_id:
        recalculate_kol_profile_stats(call.kol_id, user_id)
    return call


def list_kol_calls(user_id: int, kol_id: Optional[int] = None) -> List[KOLCall]:
    init_db()
    with get_connection() as conn:
        if kol_id:
            rows = conn.execute("SELECT * FROM kol_calls WHERE user_id = ? AND kol_id = ? ORDER BY call_time DESC, id DESC", (user_id, kol_id)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM kol_calls WHERE user_id = ? ORDER BY call_time DESC, id DESC", (user_id,)).fetchall()
    return [_call(row) for row in rows]


def get_kol_call(call_id: int, user_id: int) -> Optional[KOLCall]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM kol_calls WHERE id = ? AND user_id = ?", (call_id, user_id)).fetchone()
    return _call(row) if row else None


def update_kol_call(call_id: int, payload: KOLCallUpdate, user_id: int) -> Optional[KOLCall]:
    current = get_kol_call(call_id, user_id)
    if current is None:
        return None
    data = current.model_dump()
    data.update(payload.model_dump(exclude_unset=True))
    data = calculate_call_performance(data)
    data["updated_at"] = _now()
    fields = [
        "kol_id", "kol_name", "asset", "asset_type", "call_time", "call_price", "current_price", "source",
        "source_url", "call_text", "call_type", "time_horizon", "status", "roi_7d", "roi_30d", "current_roi",
        "max_gain", "max_drawdown", "result_label", "emotion_tags", "bias_tags", "updated_at"
    ]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE kol_calls SET {', '.join(f'{field} = ?' for field in fields)} WHERE id = ? AND user_id = ?",
            [data.get(field) for field in fields] + [call_id, user_id],
        )
        conn.commit()
    if data.get("kol_id"):
        recalculate_kol_profile_stats(data["kol_id"], user_id)
    return get_kol_call(call_id, user_id)


def delete_kol_call(call_id: int, user_id: int) -> bool:
    call = get_kol_call(call_id, user_id)
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM kol_calls WHERE id = ? AND user_id = ?", (call_id, user_id))
        conn.commit()
    if call and call.kol_id:
        recalculate_kol_profile_stats(call.kol_id, user_id)
    return cursor.rowcount > 0


def refresh_kol_call(call_id: int, user_id: int) -> Optional[KOLCall]:
    call = get_kol_call(call_id, user_id)
    if call is None:
        return None
    try:
        price = _current_price(call.asset, call.asset_type)
    except Exception:
        price = None
    data: Dict[str, Any] = {}
    if price is not None:
        data["current_price"] = price
        current_roi = _roi(call.call_price, price)
        data["current_roi"] = current_roi
        if current_roi is not None:
            data["result_label"] = "win" if current_roi > 0 else "loss"
            try:
                call_time = datetime.fromisoformat((call.call_time or "").replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - call_time.replace(tzinfo=call_time.tzinfo or timezone.utc)).days
            except Exception:
                age_days = 0
            if age_days >= 7 and call.roi_7d is None:
                data["roi_7d"] = current_roi
            if age_days >= 30 and call.roi_30d is None:
                data["roi_30d"] = current_roi
    data["status"] = "open"
    return update_kol_call(call_id, KOLCallUpdate(**data), user_id)


def calculate_trust_score(calls: List[KOLCall]) -> Dict[str, Any]:
    score = 50
    roi7 = [call.roi_7d for call in calls if call.roi_7d is not None]
    roi30 = [call.roi_30d for call in calls if call.roi_30d is not None]
    win7 = (sum(1 for value in roi7 if value > 0) / len(roi7) * 100) if roi7 else 0
    win30 = (sum(1 for value in roi30 if value > 0) / len(roi30) * 100) if roi30 else 0
    avg7 = sum(roi7) / len(roi7) if roi7 else 0
    avg30 = sum(roi30) / len(roi30) if roi30 else 0
    drawdowns = [call.max_drawdown for call in calls if call.max_drawdown is not None]
    avg_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0
    gains = [call.max_gain for call in calls if call.max_gain is not None]
    avg_gain = sum(gains) / len(gains) if gains else 0
    if roi7:
        score += 15 if win7 >= 60 else -15 if win7 < 40 else 0
    if roi30:
        score += 15 if win30 >= 60 else -15 if win30 < 40 else 0
    if avg30 > 20:
        score += 10
    elif avg30 < -10:
        score -= 10
    if avg_drawdown < -40:
        score -= 15
    elif avg_drawdown < -25:
        score -= 8
    text = " ".join(call.call_text or "" for call in calls).lower()
    if sum(word.lower() in text for word in FOMO_WORDS) >= 2:
        score -= 10
    if calls and sum(1 for call in calls if call.call_price is None) / len(calls) > 0.5:
        score -= 10
    score = clamp_score(score)
    return {
        "trust_score": score, "risk_level": _risk_level(score), "win_rate_7d": round(win7, 2),
        "win_rate_30d": round(win30, 2), "average_roi_7d": round(avg7, 2),
        "average_roi_30d": round(avg30, 2), "average_max_gain": round(avg_gain, 2),
        "average_max_drawdown": round(avg_drawdown, 2), "total_calls": len(calls),
    }


def recalculate_kol_profile_stats(kol_id: int, user_id: int) -> Optional[KOLProfile]:
    calls = list_kol_calls(user_id, kol_id)
    stats = calculate_trust_score(calls)
    stats["updated_at"] = _now()
    with get_connection() as conn:
        if conn.execute("SELECT id FROM kol_profiles WHERE id = ? AND user_id = ?", (kol_id, user_id)).fetchone() is None:
            return None
        conn.execute(
            f"UPDATE kol_profiles SET {', '.join(f'{key} = ?' for key in stats)} WHERE id = ? AND user_id = ?",
            list(stats.values()) + [kol_id, user_id],
        )
        conn.commit()
    return get_kol_profile(kol_id, user_id)


def calculate_user_kol_dependency(user_id: int) -> KOLDependencyResponse:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
        calls = conn.execute("SELECT kol_name FROM kol_calls WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
    records = [dict(row) for row in rows]
    call_names: List[str] = [row["kol_name"] for row in calls if row["kol_name"]]
    total = len(records) + len(calls)
    related = len(calls)
    names: List[str] = call_names[:]
    for row in records:
        text = " ".join(str(row.get(field) or "") for field in ["user_intent", "buy_reason", "user_text", "notes", "title"])
        if any(word.lower() in text.lower() for word in KOL_KEYWORDS):
            related += 1
            names.append("Unknown KOL")
    if total == 0:
        return KOLDependencyResponse(kol_dependency=0, kol_related_count=0, total_decisions=0, top_kol_names=[], summary="还没有足够记录判断你是否依赖 KOL。")
    dependency = clamp_score(int(related / total * 100))
    top = [name for name, _ in Counter(names).most_common(5)]
    summary = f"过去{total}次投资记录中，你有{related}次受到KOL或外部叙事影响。真正的风险不是某个KOL准不准，而是你正在把判断外包给别人。"
    return KOLDependencyResponse(kol_dependency=dependency, kol_related_count=related, total_decisions=total, top_kol_names=top, summary=summary)


def build_kol_risk_summary(text: str, user_id: int) -> Optional[Dict[str, Any]]:
    signals = extract_kol_signals_from_text(text)
    if not signals["kol_detected"]:
        return None
    profiles = list_kol_profiles(user_id)
    matched = next((p for p in profiles if p.name.lower() in text.lower()), None)
    dependency = calculate_user_kol_dependency(user_id)
    return {
        "kol_detected": True,
        "kol_name": matched.name if matched else "Unknown KOL",
        "kol_dependency_warning": dependency.summary,
        "related_kol_profile": matched.model_dump() if matched else None,
        "kol_trust_score": matched.trust_score if matched else None,
        "kol_risk_level": matched.risk_level if matched else "Unknown",
        "warning": "你这次买入理由高度依赖KOL推荐。请确认你是否有独立买入逻辑。",
    }
