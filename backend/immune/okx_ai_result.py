from typing import Any, Dict, List

from immune.direction import direction_label
from schemas import ImmuneReportRequest


def _items(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _top_biases(report: Dict[str, Any]) -> List[str]:
    biases = report.get("bias_detection", {}).get("biases") or []
    result: List[str] = []
    for item in biases[:3]:
        if isinstance(item, dict):
            bias_type = item.get("bias_type") or "Unknown Bias"
            warning = item.get("warning") or item.get("better_question") or ""
            result.append(f"{bias_type}: {warning}".strip(": "))
        else:
            result.append(str(item))
    return result


def _market_snapshot(report: Dict[str, Any]) -> str:
    raw = report.get("risk_scan", {}).get("raw_data") or {}
    source = (
        raw.get("external_market_data_source")
        or raw.get("primary_data_source")
        or raw.get("source")
        or raw.get("data_source")
        or "fallback"
    )
    parts: List[str] = []

    price = raw.get("price_usd") or raw.get("price")
    if price:
        parts.append(f"价格 {price}")
    liquidity = raw.get("liquidity")
    if liquidity:
        parts.append(f"流动性 {liquidity}")
    volume = raw.get("volume24h") or raw.get("volume")
    if volume:
        parts.append(f"成交量 {volume}")
    fdv = raw.get("fdv") or raw.get("market_cap")
    if fdv:
        parts.append(f"估值/市值 {fdv}")

    if not parts:
        return f"数据源：{source}。当前只拿到有限行情字段，不能把它当作完整研究。"
    return f"数据源：{source}。" + "；".join(parts) + "。"


def _market_link(report: Dict[str, Any]) -> str | None:
    raw = report.get("risk_scan", {}).get("raw_data") or {}
    return raw.get("pair_url") or raw.get("pool_url") or raw.get("okx_url") or raw.get("explorer_url")


def _one_line_reason(report: Dict[str, Any]) -> str:
    decision = report.get("final_decision", "")
    emotion_score = int(report.get("emotion_scan", {}).get("emotion_score") or 0)
    bias_score = int(report.get("bias_detection", {}).get("bias_score") or 0)
    conviction = int(report.get("conviction_score", {}).get("score") or 0)
    confidence = int((report.get("data_confidence") or {}).get("score") or 0)

    if decision.startswith("🔴"):
        if emotion_score >= 70:
            return "你现在最大的问题不是资产本身，而是情绪正在推着你下单。"
        if bias_score >= 70:
            return "这次决策里偏差太重，先停下来比继续找理由更重要。"
        if conviction <= 40:
            return "你还没有写出足够清楚的交易计划，现在下单更像情绪下注。"
        return "当前风险组合不适合开仓，先让计划比观点更硬。"
    if confidence < 45:
        return "数据还不够完整，等待比用半截信息开仓更聪明。"
    if decision.startswith("🟢"):
        return "计划结构相对完整，但仍只能小仓位试错，不能把观点当确定性。"
    return "现在最好的动作不是立刻交易，而是补全证据和退出规则。"


def _format_list(items: List[str], fallback: str) -> str:
    values = [item for item in items if item]
    if not values:
        values = [fallback]
    return "\n".join(f"{index}. {item}" for index, item in enumerate(values, start=1))


def _format_bullets(items: List[str], fallback: str) -> str:
    values = [item for item in items if item]
    if not values:
        values = [fallback]
    return "\n".join(f"- {item}" for item in values)


def _yes_no(value: Any) -> str:
    return "是" if bool(value) else "否"


def _format_percent(value: Any) -> str:
    if value in (None, ""):
        return "未知"
    try:
        return f"{float(value):g}%"
    except (TypeError, ValueError):
        return str(value)


def _build_okx_security_scan(report: Dict[str, Any]) -> Dict[str, Any] | None:
    raw = report.get("risk_scan", {}).get("raw_data") or {}
    okx_data = raw.get("okx_onchain") or {}
    security = raw.get("security_summary") or raw.get("okx_security_summary") or {}
    source = raw.get("security_source") or security.get("source") or raw.get("external_market_data_source")
    if not security and not raw.get("liquidity_change_24h") and not raw.get("pool_depth_warning"):
        return None

    liquidity_change = raw.get("liquidity_change_24h")
    pool_depth = raw.get("pool_depth_usd")
    pool_depth_warning = bool(raw.get("pool_depth_warning"))
    top10_hold = okx_data.get("top10_hold_percent")
    risk_level = okx_data.get("risk_control_level")

    warning_items: List[str] = []
    if security.get("is_honeypot"):
        warning_items.append("疑似蜜罐，可能买入后难以卖出")
    if security.get("is_blacklisted"):
        warning_items.append("存在黑名单风险，部分地址可能被限制交易")
    if security.get("is_mintable"):
        warning_items.append("合约可能存在增发权限，持有人可能被稀释")
    if security.get("is_proxy"):
        warning_items.append("代理合约风险，合约逻辑可能被升级改变")
    if security.get("can_take_back_ownership") or security.get("owner_change_balance"):
        warning_items.append("owner 权限较强，可能影响合约控制权或持有人余额")
    buy_tax = security.get("buy_tax_percent")
    sell_tax = security.get("sell_tax_percent")
    if (buy_tax or 0) > 10 or (sell_tax or 0) > 10:
        warning_items.append(f"买卖税偏高：买税 {_format_percent(buy_tax)}，卖税 {_format_percent(sell_tax)}")
    if top10_hold is not None and top10_hold > 40:
        warning_items.append(f"Top 10 持仓占比约 {_format_percent(top10_hold)}，筹码集中度偏高")
    if liquidity_change is not None and liquidity_change < -25:
        warning_items.append(f"24h 流动性下降约 {_format_percent(abs(liquidity_change))}，需要警惕撤池或深度变薄")
    if pool_depth_warning or (pool_depth is not None and pool_depth < 50_000):
        warning_items.append("池子深度不足，较小资金也可能造成明显滑点")
    if risk_level is not None and risk_level >= 4:
        warning_items.append("OKX 风险等级为高风险，不能只看价格涨跌")

    if not warning_items:
        warning_items.append("未发现明显合约安全红灯，但仍需要结合仓位和退出计划。")

    return {
        "source": source or "OKX Onchain OS Agent",
        "honeypot": bool(security.get("is_honeypot")),
        "blacklist": bool(security.get("is_blacklisted")),
        "mintable": bool(security.get("is_mintable")),
        "proxy_contract": bool(security.get("is_proxy")),
        "owner_privilege": security.get("owner_privilege") or (
            "high" if security.get("can_take_back_ownership") or security.get("owner_change_balance") else "low"
        ),
        "buy_tax_percent": buy_tax,
        "sell_tax_percent": sell_tax,
        "liquidity_change_24h": liquidity_change,
        "pool_depth_usd": pool_depth,
        "pool_depth_warning": pool_depth_warning,
        "top10_hold_percent": top10_hold,
        "risk_control_level": risk_level,
        "warnings": warning_items,
        "summary": "；".join(warning_items[:4]),
    }


def _build_okx_agent_next_action(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    raw = report.get("risk_scan", {}).get("raw_data") or {}
    used_external = bool(raw.get("external_market_data_used"))
    asset = report.get("asset") or payload.asset
    asset_type = report.get("asset_type") or payload.asset_type
    if used_external:
        return {
            "required": False,
            "action": "none",
            "message": "已收到调用方 Agent 传入的 external_market_data，本次报告已优先使用外部 OKX 数据。",
        }
    if asset_type == "crypto":
        data_request = "价格、24h 成交量、流动性、市值/FDV、持有人、Top10 持仓、风险等级、合约安全、交易池链接"
        okx_tool_hint = "OKX Market / DEX / OnchainOS"
    elif asset_type == "stock":
        data_request = "价格、涨跌幅、成交量、市值、PE、营收增长、利润率、负债、分析师共识"
        okx_tool_hint = "OKX Market"
    else:
        data_request = "最新价格、成交量、市值、估值、风险字段和可验证链接"
        okx_tool_hint = "OKX Market"
    return {
        "required": True,
        "action": "query_okx_market_data_and_retry",
        "message": f"为了提高数据质量，请先用 {okx_tool_hint} 查询 {asset} 的最新数据，再把结果作为 external_market_data 重新调用 /immune/report。",
        "asset": asset,
        "asset_type": asset_type,
        "requested_fields": data_request,
        "retry_payload_hint": {
            "asset": asset,
            "asset_type": asset_type,
            "trade_direction": payload.trade_direction,
            "user_text": payload.user_text,
            "buy_reason": payload.buy_reason,
            "position_size": payload.position_size,
            "risk_awareness": payload.risk_awareness,
            "worst_case_plan": payload.worst_case_plan,
            "external_market_data": {
                "source": "OKX Market Agent",
                "symbol": asset,
                "price": "...",
                "volume24h": "...",
                "market_cap": "...",
                "liquidity": "...",
                "pair_url": "https://www.okx.com/...",
            },
        },
    }


def _format_okx_security_markdown(security_scan: Dict[str, Any] | None) -> List[str]:
    if not security_scan:
        return []
    warnings = _items(security_scan.get("warnings"))[:6]
    return [
        "## OKX 安全扫描",
        f"- 数据源：{security_scan.get('source')}",
        f"- 疑似蜜罐：{_yes_no(security_scan.get('honeypot'))}",
        f"- 黑名单风险：{_yes_no(security_scan.get('blacklist'))}",
        f"- Owner 权限：{security_scan.get('owner_privilege') or '未知'}",
        f"- 买税/卖税：{_format_percent(security_scan.get('buy_tax_percent'))} / {_format_percent(security_scan.get('sell_tax_percent'))}",
        f"- 24h 流动性变化：{_format_percent(security_scan.get('liquidity_change_24h'))}",
        f"- 池子深度风险：{_yes_no(security_scan.get('pool_depth_warning'))}",
        "- 关键提醒：" + ("；".join(warnings) if warnings else "未发现明显合约安全红灯。"),
        "",
    ]


def _build_display_markdown(
    payload: ImmuneReportRequest,
    result: Dict[str, Any],
    report: Dict[str, Any],
    what_is_missing: List[str],
) -> str:
    asset = result.get("asset") or payload.asset.upper()
    decision = result.get("decision") or report.get("final_decision")
    headline = result.get("headline") or _one_line_reason(report)
    confidence = result.get("data_confidence") or {}
    behavior = result.get("behavior_scan") or {}
    top_risks = _items(result.get("top_risks"))[:4]
    must_answer = _items(result.get("must_answer_before_trade"))[:3]
    emotions = _items(behavior.get("detected_emotions"))[:4]
    biases = _items(behavior.get("top_biases"))[:3]
    security_section = _format_okx_security_markdown(result.get("okx_security_scan"))
    next_action = result.get("okx_agent_next_action") or {}
    okx_retry_line = (
        f"- OKX Agent 下一步：{next_action.get('message')}"
        if next_action.get("required")
        else ""
    )

    return "\n".join(
        [
            f"# {decision} {asset}",
            "",
            headline,
            "",
            "## 市场数据",
            f"- {result.get('market_snapshot')}",
            okx_retry_line,
            f"- 查看交易池/合约：{result.get('market_link')}" if result.get("market_link") else "",
            f"- 数据置信度：{confidence.get('score')} / {confidence.get('level')}",
            f"- 数据提示：{confidence.get('summary')}",
            "",
            *security_section,
            "## 为什么现在不该冲动",
            _format_list(top_risks, "当前证据还不足以支持重仓开仓。"),
            "",
            "## 行为风险",
            f"- 情绪分：{behavior.get('emotion_score')}",
            f"- 识别情绪：{', '.join(emotions) if emotions else '未触发明显情绪标签'}",
            f"- 偏差分：{behavior.get('bias_score')}",
            f"- 主要偏差：{'; '.join(biases) if biases else '未触发明显偏差'}",
            f"- KOL 提醒：{behavior.get('kol_warning') or '未匹配到具体 KOL 画像，但仍要确认这是不是外部叙事驱动。'}",
            "",
            "## 下单前必须回答",
            _format_bullets(must_answer, "什么事实出现后，你会承认自己错了？"),
            "",
            "## 迷你投资笔记",
            f"- 开仓理由：{payload.buy_reason or payload.user_intent or '未填写'}",
            f"- 仓位规模：{payload.position_size or '未填写'}",
            f"- 最坏情况计划：{payload.worst_case_plan or '未填写'}",
            f"- 当前缺口：{'; '.join(what_is_missing[:4])}",
            "",
            "## 下一步",
            f"{result.get('next_step')}",
            "",
            "这不是预测价格的工具。它帮你在下单前停一下，在复盘后变聪明一点。",
        ]
    )


def build_okx_ai_agent_result(payload: ImmuneReportRequest, report: Dict[str, Any]) -> Dict[str, Any]:
    direction = direction_label(report.get("trade_direction") or payload.trade_direction)
    risk_reasons = _items(report.get("risk_scan", {}).get("risk_reasons"))[:4]
    emotions = _items(report.get("emotion_scan", {}).get("detected_emotions"))[:4]
    confidence = report.get("data_confidence") or {}
    coach = report.get("ai_coach") or {}
    history = report.get("historical_dna_scan") or {}
    kol_scan = report.get("kol_risk_scan") or {}
    okx_security_scan = _build_okx_security_scan(report)
    okx_agent_next_action = _build_okx_agent_next_action(payload, report)

    must_answer = report.get("devil_advocate", {}).get("killer_questions") or []
    if not must_answer:
        must_answer = [
            "如果价格朝反方向走 25%，你会怎么处理？",
            "什么事实出现后，你会承认自己错了？",
            "这笔仓位亏损后，会不会影响下一次理性决策？",
        ]

    what_is_missing: List[str] = []
    for problem in _items(report.get("conviction_score", {}).get("problems"))[:3]:
        what_is_missing.append(problem)
    if confidence.get("missing"):
        what_is_missing.append("数据缺口：" + "、".join(_items(confidence.get("missing"))[:3]))
    if not what_is_missing:
        what_is_missing.append("继续保持：理由、仓位、反向情景和复盘条件都要写清楚。")

    result = {
        "service_name": "Investment Immune Scan",
        "designed_for": "OKX.AI A2MCP",
        "headline": _one_line_reason(report),
        "decision": report.get("final_decision"),
        "asset": report.get("asset"),
        "asset_type": report.get("asset_type"),
        "direction": direction,
        "market_snapshot": _market_snapshot(report),
        "market_link": _market_link(report),
        "data_confidence": {
            "score": confidence.get("score"),
            "level": confidence.get("level"),
            "summary": confidence.get("summary"),
        },
        "okx_security_scan": okx_security_scan,
        "okx_agent_next_action": okx_agent_next_action,
        "top_risks": risk_reasons,
        "behavior_scan": {
            "emotion_score": report.get("emotion_scan", {}).get("emotion_score"),
            "detected_emotions": emotions,
            "bias_score": report.get("bias_detection", {}).get("bias_score"),
            "top_biases": _top_biases(report),
            "kol_warning": kol_scan.get("warning") if isinstance(kol_scan, dict) else None,
        },
        "why_stop_or_wait": report.get("decision_reason"),
        "position_advice": report.get("position_advice"),
        "must_answer_before_trade": _items(must_answer)[:3],
        "mini_notebook": {
            "what_user_wrote": {
                "intent": payload.user_intent,
                "reason": payload.buy_reason,
                "position_size": payload.position_size,
                "worst_case_plan": payload.worst_case_plan,
                "favorable_plan": payload.favorable_plan,
                "sideways_plan": payload.sideways_plan,
            },
            "what_is_missing": what_is_missing,
            "review_later": "7 天后复盘：你是否按计划执行，而不是按情绪改规则。",
        },
        "mini_dna_update": {
            "historical_patterns": history.get("triggered_patterns", []),
            "risk_adjustment": history.get("risk_adjustment", 0),
            "summary": history.get("summary"),
        },
        "coach_message": coach.get("coach_message"),
        "next_step": coach.get("next_action") or "先等待 24 小时，再重新扫描同一个资产。",
        "full_product_url": "https://global-asset-shield.onrender.com",
    }
    result["short_answer"] = f"{result['decision']} {result['asset']}。{result['headline']}"
    result["recommended_display_field"] = "okx_ai_agent_result.display_markdown"
    result["demo_ready_summary"] = (
        f"{result['decision']} {result['asset']}：{result['headline']} "
        f"系统已综合市场数据、情绪风险、认知偏差、仓位风险和历史 DNA，给出下单前免疫提醒。"
    )
    result["display_markdown"] = _build_display_markdown(payload, result, report, what_is_missing)
    return result
