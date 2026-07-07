import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import get_connection, init_db
from scanner.cn_stock import scan_cn_stock
from scanner.crypto import scan_crypto
from scanner.historical import historical_roi
from scanner.stock import scan_stock
from scanner.utils import clamp_score
from schemas import KOLBatchCaptureRequest, KOLCall, KOLCallCreate, KOLCallUpdate, KOLCaptureRequest, KOLDependencyResponse, KOLProfile, KOLProfileCreate, KOLProfileUpdate


KOL_KEYWORDS = ["KOL", "kol", "博主", "大V", "老师", "群里", "朋友推荐", "喊单", "推特", "Twitter", "x.com", "YouTube", "Telegram"]
FOMO_WORDS = ["100x", "10x", "moon", "last chance", "never sell", "暴富", "财富自由", "起飞", "梭哈"]
AUTHORITY_WORDS = ["KOL", "kol", "博主", "大V", "老师", "群里", "喊单", "alpha", "insider"]
LOTTERY_WORDS = ["100x", "10x", "moon", "暴富", "财富自由", "翻倍", "百倍"]
BUY_WORDS = ["buy", "long", "accumulate", "ape", "上车", "买", "加仓", "冲"]
SELL_WORDS = ["sell", "short", "dump", "卖", "做空", "清仓"]
WARNING_WORDS = ["avoid", "warning", "risk", "别买", "小心", "危险"]
ASSET_STOPWORDS = {
    "KOL", "FOMO", "BUY", "SELL", "HOLD", "LONG", "SHORT", "MOON", "LAST", "CHANCE",
    "AI", "ROI", "USD", "USDT",
}


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
    lottery = [word for word in LOTTERY_WORDS if word.lower() in haystack.lower()]
    authority = [word for word in AUTHORITY_WORDS if word.lower() in haystack.lower()]
    emotions = []
    biases = []
    if fomo:
        emotions.append("FOMO")
    if authority or kol_detected:
        biases.append("Authority Bias")
    if lottery:
        biases.append("Lottery Bias")
    return {
        "kol_detected": kol_detected,
        "emotion_tags": emotions,
        "bias_tags": biases,
        "fomo_words": fomo,
        "lottery_words": lottery,
        "authority_words": authority,
    }


def infer_asset_from_call_text(text: str) -> str:
    haystack = text or ""
    cashtag = re.search(r"\$([A-Za-z][A-Za-z0-9]{1,12})\b", haystack)
    if cashtag:
        return cashtag.group(1).upper()
    words = re.findall(r"\b[A-Z][A-Z0-9]{1,12}\b", haystack)
    for word in words:
        if word not in ASSET_STOPWORDS:
            return word.upper()
    return "UNKNOWN"


def infer_call_type(text: str) -> str:
    lowered = (text or "").lower()
    if any(word.lower() in lowered for word in WARNING_WORDS):
        return "warning"
    if any(word.lower() in lowered for word in SELL_WORDS):
        return "sell"
    if any(word.lower() in lowered for word in LOTTERY_WORDS):
        return "moonshot"
    if any(word.lower() in lowered for word in BUY_WORDS):
        return "buy"
    return "unknown"


def infer_time_horizon(text: str) -> str:
    lowered = (text or "").lower()
    if any(word in lowered for word in ["today", "24h", "短线", "今晚", "马上"]):
        return "short"
    if any(word in lowered for word in ["month", "30d", "swing", "波段"]):
        return "medium"
    if any(word in lowered for word in ["cycle", "long term", "长期", "周期"]):
        return "long"
    return "unknown"


def _parse_history_line(line: str) -> Optional[Dict[str, Any]]:
    cleaned = line.strip()
    if not cleaned:
        return None
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?\s+(.*)$", cleaned)
    call_time = None
    body = cleaned
    if date_match:
        time_part = date_match.group(2) or "00:00:00"
        if len(time_part) == 5:
            time_part = f"{time_part}:00"
        call_time = f"{date_match.group(1)}T{time_part}+00:00"
        body = date_match.group(3).strip()

    asset = infer_asset_from_call_text(body)
    price = None
    text_after_asset = body
    price_match = re.search(r"(?:\$?[A-Z][A-Z0-9]{1,12}\s+)([0-9]+(?:\.[0-9]+)?)\b(.*)$", body)
    if price_match:
        try:
            price = float(price_match.group(1))
            text_after_asset = f"{asset} {price_match.group(2).strip()}".strip()
        except ValueError:
            price = None

    return {
        "asset": asset,
        "call_price": price,
        "call_time": call_time,
        "call_text": text_after_asset or body,
    }


def _current_price(asset: str, asset_type: str) -> Optional[float]:
    try:
        if asset_type == "crypto":
            scan = scan_crypto(asset)
        elif asset_type == "cn_stock":
            scan = scan_cn_stock(asset)
        else:
            scan = scan_stock(asset)
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


def _merge_json_tags(raw_tags: Optional[str], tag: str) -> str:
    try:
        tags = json.loads(raw_tags or "[]")
    except Exception:
        tags = []
    if tag not in tags:
        tags.append(tag)
    return json.dumps(tags, ensure_ascii=False)


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
    if data.get("current_price") is None and data.get("source") != "manual_history":
        data["current_price"] = _current_price(data["asset"], data.get("asset_type") or "crypto")
    data = calculate_call_performance(data)
    if data.get("kol_id"):
        data["bias_tags"] = _merge_json_tags(data.get("bias_tags"), "Authority Bias")
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


def capture_kol_call(payload: KOLCaptureRequest, user_id: int) -> KOLCall:
    text = payload.call_text.strip()
    asset = (payload.asset or infer_asset_from_call_text(text)).upper()
    call_type = infer_call_type(text)
    horizon = payload.time_horizon or infer_time_horizon(text)
    return create_kol_call(
        KOLCallCreate(
            kol_id=payload.kol_id,
            kol_name=payload.kol_name,
            asset=asset,
            asset_type=payload.asset_type,
            call_price=payload.call_price,
            current_price=payload.current_price,
            source="manual",
            call_text=text,
            call_type=call_type,
            time_horizon=horizon,
            status="open",
        ),
        user_id,
    )


def capture_kol_calls_batch(payload: KOLBatchCaptureRequest, user_id: int) -> Dict[str, Any]:
    created: List[KOLCall] = []
    skipped: List[str] = []
    for line in payload.text.splitlines():
        parsed = _parse_history_line(line)
        if not parsed:
            continue
        if parsed["asset"] == "UNKNOWN":
            skipped.append(line)
            continue
        call = create_kol_call(
            KOLCallCreate(
                kol_id=payload.kol_id,
                kol_name=payload.kol_name,
                asset=parsed["asset"],
                asset_type=payload.asset_type,
                call_time=parsed["call_time"],
                call_price=parsed["call_price"],
                source="manual_history",
                call_text=parsed["call_text"],
                call_type=infer_call_type(parsed["call_text"]),
                time_horizon=infer_time_horizon(parsed["call_text"]),
                status="open",
            ),
            user_id,
        )
        created.append(call)

    profile = build_kol_behavior_profile(payload.kol_id, user_id) if payload.kol_id else build_kol_behavior_profile_from_calls(created)
    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "skipped_lines": skipped,
        "calls": [call.model_dump() for call in created],
        "kol_risk_profile": profile,
        "summary": profile["summary"],
    }


def _json_list(raw: Optional[str]) -> List[str]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0


def build_kol_behavior_profile_from_calls(calls: List[KOLCall]) -> Dict[str, Any]:
    total = len(calls)
    if total == 0:
        return {
            "profile_type": "No Record",
            "leek_risk_score": 0,
            "high_emotion_ratio": 0,
            "win_rate": 0,
            "average_roi": 0,
            "red_flags": [],
            "summary": "还没有历史喊单，不能判断这个 KOL 的行为模式。",
        }

    fomo_count = sum(1 for call in calls if "FOMO" in _json_list(call.emotion_tags))
    lottery_count = sum(1 for call in calls if "Lottery Bias" in _json_list(call.bias_tags))
    missing_price_count = sum(1 for call in calls if call.call_price is None)
    roi_values = [float(call.current_roi) for call in calls if call.current_roi is not None]
    completed = [value for value in roi_values]
    wins = sum(1 for value in completed if value > 0)
    losses = sum(1 for value in completed if value <= 0)
    avg_roi = _mean(roi_values)
    high_emotion_ratio = (fomo_count + lottery_count) / max(total, 1) * 100
    win_rate = wins / len(completed) * 100 if completed else 0

    score = 0
    red_flags: List[str] = []
    if high_emotion_ratio >= 50:
        score += 30
        red_flags.append("高情绪喊单比例偏高")
    if completed and win_rate < 40:
        score += 25
        red_flags.append("历史胜率偏低")
    if roi_values and avg_roi < 0:
        score += 20
        red_flags.append("平均 ROI 为负")
    if missing_price_count / total > 0.5:
        score += 15
        red_flags.append("多数喊单没有记录入场价格")
    if total >= 5 and high_emotion_ratio >= 60:
        score += 10
        red_flags.append("高频叙事动员，容易放大用户冲动")
    score = clamp_score(score)

    if score >= 75:
        profile_type = "Pump Risk"
    elif high_emotion_ratio >= 55:
        profile_type = "FOMO Promoter"
    elif completed and win_rate >= 60 and avg_roi > 0:
        profile_type = "Research Analyst"
    elif completed:
        profile_type = "Mixed Record"
    else:
        profile_type = "Narrative Chaser"

    if profile_type == "Pump Risk":
        summary = f"这个 KOL 过去 {total} 次记录里，高情绪喊单比例 {high_emotion_ratio:.0f}%，胜率 {win_rate:.0f}%。这不是稳定研究，更像情绪动员。"
    elif profile_type == "Research Analyst":
        summary = f"这个 KOL 过去 {total} 次记录里，胜率 {win_rate:.0f}%，平均 ROI {avg_roi:.2f}%。可以参考观点，但仍不能替代你的退出计划。"
    else:
        summary = f"这个 KOL 过去 {total} 次记录里，高情绪喊单比例 {high_emotion_ratio:.0f}%，平均 ROI {avg_roi:.2f}%。观点可以看，但不要把它当买入理由。"

    if score >= 60:
        summary += " 疑似割韭菜风险较高：真正的问题不是他会不会喊对，而是他是否在制造你的冲动。"

    return {
        "profile_type": profile_type,
        "leek_risk_score": score,
        "high_emotion_ratio": round(high_emotion_ratio, 2),
        "win_rate": round(win_rate, 2),
        "average_roi": round(avg_roi, 2),
        "red_flags": red_flags,
        "summary": summary,
    }


def build_kol_behavior_profile(kol_id: Optional[int], user_id: int) -> Dict[str, Any]:
    if not kol_id:
        return build_kol_behavior_profile_from_calls([])
    return build_kol_behavior_profile_from_calls(list_kol_calls(user_id, kol_id))


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
                roi_7d = historical_roi(call.asset, call.asset_type, call.call_price, call.call_time, 7)
                data["roi_7d"] = roi_7d if roi_7d is not None else current_roi
            if age_days >= 30 and call.roi_30d is None:
                roi_30d = historical_roi(call.asset, call.asset_type, call.call_price, call.call_time, 30)
                data["roi_30d"] = roi_30d if roi_30d is not None else current_roi
    if call.roi_7d is None:
        roi_7d = historical_roi(call.asset, call.asset_type, call.call_price, call.call_time, 7)
        if roi_7d is not None:
            data["roi_7d"] = roi_7d
    if call.roi_30d is None:
        roi_30d = historical_roi(call.asset, call.asset_type, call.call_price, call.call_time, 30)
        if roi_30d is not None:
            data["roi_30d"] = roi_30d
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
