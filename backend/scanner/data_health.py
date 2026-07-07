from typing import Any, Dict, List

import requests

from config import DEEPSEEK_API_BASE, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from database import is_database_connected
from scanner.stock import fetch_yahoo_chart_stock


def build_data_health() -> Dict[str, Any]:
    checks = [
        _check_database(),
        _check_deepseek(),
        _check_dexscreener(),
        _check_goplus(),
        _check_yahoo_chart(),
    ]
    degraded_count = len([item for item in checks if item["status"] != "connected"])
    overall = "connected" if degraded_count == 0 else "degraded"
    return {
        "overall_status": overall,
        "summary": _summary(checks),
        "sources": checks,
    }


def _source(name: str, status: str, detail: str, live_data: bool, fallback_available: bool = True) -> Dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "live_data": live_data,
        "fallback_available": fallback_available,
    }


def _check_database() -> Dict[str, Any]:
    if is_database_connected():
        return _source("Database", "connected", "用户、Journal、Notebook、DNA、KOL 数据库可用。", True, False)
    return _source("Database", "down", "数据库暂时不可用，用户数据无法保存。", False, False)


def _check_deepseek() -> Dict[str, Any]:
    if not DEEPSEEK_API_KEY:
        return _source("DeepSeek AI Coach", "fallback", "未配置 API Key，报告会使用规则版 AI Coach。", False, True)
    try:
        response = requests.post(
            DEEPSEEK_API_BASE.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": "OK"}],
                "max_tokens": 2,
                "temperature": 0,
                "stream": False,
            },
            timeout=12,
        )
        if response.ok:
            return _source("DeepSeek AI Coach", "connected", f"DeepSeek API 可用，模型 {DEEPSEEK_MODEL}。", True, True)
        text = response.text.lower()
        if response.status_code == 402 or "insufficient" in text or "balance" in text:
            return _source("DeepSeek AI Coach", "needs_balance", "DeepSeek API 已连通，但账户余额不足；系统会使用规则版 AI Coach。", False, True)
        return _source("DeepSeek AI Coach", "degraded", f"DeepSeek 返回 {response.status_code}，系统会使用规则版 AI Coach。", False, True)
    except Exception as exc:
        return _source("DeepSeek AI Coach", "degraded", f"DeepSeek 暂时不可达：{exc.__class__.__name__}，系统会使用规则版 AI Coach。", False, True)


def _check_dexscreener() -> Dict[str, Any]:
    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/search", params={"q": "PEPE"}, timeout=12)
        response.raise_for_status()
        pairs = (response.json() or {}).get("pairs") or []
        if pairs:
            return _source("DexScreener Crypto Market", "connected", f"Crypto 行情可用，测试返回 {len(pairs)} 个交易对。", True, True)
        return _source("DexScreener Crypto Market", "degraded", "接口可达，但测试没有返回交易对。", False, True)
    except Exception as exc:
        return _source("DexScreener Crypto Market", "degraded", f"DexScreener 暂时不可达：{exc.__class__.__name__}，Crypto 会使用 mock fallback。", False, True)


def _check_goplus() -> Dict[str, Any]:
    try:
        response = requests.get(
            "https://api.gopluslabs.io/api/v1/token_security/1",
            params={"contract_addresses": "0xdAC17F958D2ee523a2206206994597C13D831ec7"},
            timeout=12,
        )
        response.raise_for_status()
        result = (response.json() or {}).get("result") or {}
        if result:
            return _source("GoPlus Token Security", "connected", "合约安全检测可用。", True, True)
        return _source("GoPlus Token Security", "degraded", "GoPlus 可达，但测试没有返回安全数据。", False, True)
    except Exception as exc:
        return _source("GoPlus Token Security", "degraded", f"GoPlus 暂时不可达：{exc.__class__.__name__}，合约安全会使用占位 fallback。", False, True)


def _check_yahoo_chart() -> Dict[str, Any]:
    try:
        data = fetch_yahoo_chart_stock("NVDA")
        if data.get("price") is not None:
            return _source("Yahoo Chart US Stock Backup", "connected", f"美股备用价格源可用，NVDA 最近价格 {data['price']}。", True, True)
        return _source("Yahoo Chart US Stock Backup", "degraded", "Yahoo Chart 可达，但测试没有返回价格。", False, True)
    except Exception as exc:
        return _source("Yahoo Chart US Stock Backup", "degraded", f"Yahoo Chart 暂时不可达：{exc.__class__.__name__}，美股会继续使用 mock fallback。", False, True)


def _summary(checks: List[Dict[str, Any]]) -> str:
    connected = len([item for item in checks if item["status"] == "connected"])
    total = len(checks)
    if connected == total:
        return "所有核心数据源在线，系统正在使用真实联网数据。"
    return f"{connected}/{total} 个核心数据源在线。离线或余额不足的数据源会自动 fallback，不会阻断免疫报告。"
