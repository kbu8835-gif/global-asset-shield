from typing import Dict, List, Optional

from immune.direction import normalize_trade_direction


Outcome = Dict[str, str]


LONG_OUTCOMES: List[Dict[str, object]] = [
    {
        "market": "上涨",
        "behavior": "提前卖飞",
        "mistake": "提前卖飞",
        "keywords": ["卖飞", "卖早", "提前卖", "提前止盈", "刚卖就涨", "拿不住", "止盈太早", "少赚"],
        "lesson": "上涨后卖飞，通常不是判断问题，而是你没有提前写清楚分批止盈和继续持有的条件。",
        "next_action": "下次做多前，先写：上涨多少分批止盈，剩余仓位用什么条件继续持有。",
    },
    {
        "market": "上涨",
        "behavior": "一直持有",
        "mistake": "按计划持有",
        "keywords": ["一直持有", "继续拿", "拿住", "没卖", "按计划持有", "拿到现在", "继续持仓"],
        "lesson": "上涨后能按计划持有是好事，但不要把一次盈利误认为以后都能扛住波动。",
        "next_action": "下次盈利后，记录你为什么继续持有，以及什么条件会让你减仓。",
    },
    {
        "market": "上涨",
        "behavior": "加仓",
        "mistake": "盈利后加仓冲动",
        "keywords": ["加仓", "追涨加仓", "继续买", "又买", "加了仓", "盈利后加仓", "涨了又买"],
        "lesson": "上涨后加仓最容易把盈利交易变成情绪交易。真正要复盘的是加仓是否来自计划，而不是兴奋。",
        "next_action": "下次只允许按预先写好的加仓条件执行；如果只是因为涨了，就延迟 24 小时。",
    },
    {
        "market": "横盘",
        "behavior": "耐心等待",
        "mistake": "横盘中保持纪律",
        "keywords": ["横盘耐心", "耐心等待", "继续等", "按计划等", "没动", "继续观察", "震荡等待"],
        "lesson": "横盘时能等待，说明你没有被无聊逼着乱动。接下来要确认等待条件是否仍然有效。",
        "next_action": "下次横盘时，写清楚继续等待的截止时间和触发行动的数据。",
    },
    {
        "market": "横盘",
        "behavior": "失去耐心卖出",
        "mistake": "横盘失去耐心",
        "keywords": ["失去耐心", "没耐心", "磨人", "熬不住", "横盘卖", "震荡卖", "卖掉了", "清仓了"],
        "lesson": "横盘卖出不一定错，但如果原因只是没耐心，说明你没有把持有周期写清楚。",
        "next_action": "下次开仓前，先写最长等待时间；时间没到，不因为无聊交易。",
    },
    {
        "market": "横盘",
        "behavior": "不断加仓",
        "mistake": "横盘中不断加仓",
        "keywords": ["不断加仓", "一直加仓", "越等越买", "横盘加仓", "震荡加仓", "没动就加"],
        "lesson": "横盘不断加仓，往往是在用更多仓位弥补没有结果的焦虑。",
        "next_action": "下次横盘时，禁止用加仓解决焦虑；只有新证据出现，才允许增加仓位。",
    },
    {
        "market": "下跌",
        "behavior": "爆仓",
        "mistake": "杠杆爆仓",
        "keywords": ["爆仓", "强平", "穿仓", "杠杆爆", "保证金没了", "被清算"],
        "lesson": "爆仓不是普通亏损，而是仓位、杠杆和止损同时失控。",
        "next_action": "下次使用杠杆前，先写最大亏损金额；写不出来，不能上杠杆。",
    },
    {
        "market": "下跌",
        "behavior": "止损",
        "mistake": "按计划止损",
        "keywords": ["止损", "触发止损", "按计划卖", "按计划退", "退出了", "纪律止损", "认错离场"],
        "lesson": "亏损后能按计划止损，是投资免疫系统真正生效的表现。",
        "next_action": "下次继续保留这条规则：先写退出条件，再允许开仓。",
    },
    {
        "market": "下跌",
        "behavior": "死扛",
        "mistake": "下跌死扛",
        "keywords": ["死扛", "硬扛", "扛单", "扛着", "不卖", "装死", "一直拿着亏", "舍不得卖"],
        "lesson": "死扛的问题不是亏损本身，而是你把承认错误拖成了更大的亏损。",
        "next_action": "下次亏损达到计划线时，只执行退出，不重新解释理由。",
    },
    {
        "market": "下跌",
        "behavior": "补仓",
        "mistake": "下跌补仓",
        "keywords": ["补仓", "摊平", "越跌越买", "接飞刀", "补了", "低位加仓", "跌了再买"],
        "lesson": "补仓只有在原计划里写过才叫策略，否则就是用更多钱证明自己没错。",
        "next_action": "下次补仓前必须写新证据；如果只是因为亏了，自动禁止补仓。",
    },
    {
        "market": "下跌",
        "behavior": "割肉",
        "mistake": "恐慌割肉",
        "keywords": ["割肉", "恐慌卖", "受不了卖", "亏损卖", "吓跑", "砍仓", "亏太多卖了"],
        "lesson": "割肉可能是必要止损，也可能是没有计划后的恐慌反应。区别在于它是否提前写过。",
        "next_action": "下次把止损写成价格、比例或条件；不要等情绪替你按卖出键。",
    },
]


SHORT_OUTCOMES: List[Dict[str, object]] = [
    {
        "market": "下跌",
        "behavior": "提前止盈",
        "mistake": "做空提前止盈",
        "keywords": ["提前止盈", "早平", "平早", "提前平仓", "提前平", "刚平就跌", "少赚", "空单卖飞", "提前卖飞", "卖飞", "卖早", "拿不住空单"],
        "lesson": "做空盈利后太早平仓，通常说明你不是看错方向，而是没有提前写清楚盈利后怎么拿。",
        "next_action": "下次做空前，沿用三条就够：下跌到计划位先止盈，横盘到期限就重新评估，上涨到止损线就认错。不要临场新增规则。",
    },
    {
        "market": "下跌",
        "behavior": "一直拿",
        "mistake": "空单按计划持有",
        "keywords": ["一直拿", "继续拿", "没平", "继续持有空单", "按计划拿", "拿到现在"],
        "lesson": "下跌后能按计划持有空单是纪律，但仍要防止贪婪把盈利变回亏损。",
        "next_action": "下次盈利后，记录移动止盈条件，而不是只靠感觉继续拿。",
    },
    {
        "market": "下跌",
        "behavior": "加空",
        "mistake": "盈利后加空冲动",
        "keywords": ["加空", "继续空", "浮盈加空", "跌了加空", "又开空", "追加空单"],
        "lesson": "盈利后加空最容易把判断变成贪婪。加空必须来自计划，而不是因为行情顺着你走。",
        "next_action": "下次加空前，先写新增风险和止损位置；写不出来，不能加空。",
    },
    {
        "market": "横盘",
        "behavior": "平仓",
        "mistake": "横盘平仓",
        "keywords": ["横盘平仓", "震荡平仓", "平仓", "平了", "关仓", "没耐心平", "磨平了"],
        "lesson": "横盘平仓不一定错，但如果只是因为没耐心，说明你没有定义做空失效时间。",
        "next_action": "下次做空前，写清楚横盘多久就退出，以及退出后是否允许重新进场。",
    },
    {
        "market": "横盘",
        "behavior": "等待",
        "mistake": "横盘等待",
        "keywords": ["横盘等待", "震荡等待", "继续等", "没动", "按计划等", "等待破位"],
        "lesson": "横盘等待说明你暂时没有乱动，但等待必须有截止条件。",
        "next_action": "下次等待前，写清楚触发平仓或继续持有的条件。",
    },
    {
        "market": "上涨",
        "behavior": "爆仓",
        "mistake": "做空爆仓",
        "keywords": ["爆仓", "强平", "穿仓", "被清算", "保证金没了"],
        "lesson": "做空爆仓说明上涨风险、杠杆和止损同时失控。",
        "next_action": "下次做空前，先写最大亏损金额；超过就退出，不允许补空。",
    },
    {
        "market": "上涨",
        "behavior": "止损",
        "mistake": "做空按计划止损",
        "keywords": ["止损", "平空止损", "认错", "止损出局", "按计划平空", "按计划退出"],
        "lesson": "做空亏损后能止损，是纪律，不是失败。",
        "next_action": "下次继续保留这条规则：上涨到认错线就平空，不重新找理由。",
    },
    {
        "market": "上涨",
        "behavior": "扛单",
        "mistake": "做空扛单",
        "keywords": ["扛单", "硬扛", "死扛", "不平", "扛着", "一直扛", "亏着拿"],
        "lesson": "做空扛单的危险在于亏损没有上限，不能用意志力对抗价格。",
        "next_action": "下次做空前，把上涨止损线写死；触发后只执行，不争辩。",
    },
    {
        "market": "上涨",
        "behavior": "补空",
        "mistake": "逆势补空",
        "keywords": ["补空", "越涨越空", "加空", "上涨加空", "继续空", "又加了空"],
        "lesson": "上涨时补空不是勇敢，而是在用更大风险证明自己没错。",
        "next_action": "下次空单亏损时禁止补空；只有重新完成一份计划，才允许重新评估。",
    },
]


def _has_any(text: str, words: List[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def _preferred_market(text: str, direction: str) -> Optional[str]:
    if _has_any(text, ["横盘", "震荡", "盘整", "没动", "磨了很久", "磨人"]):
        return "横盘"
    if _has_any(text, ["上涨", "涨", "反弹", "拉升", "冲高", "逼空", "pump"]):
        return "上涨"
    if _has_any(text, ["下跌", "跌", "回撤", "破位", "dump"]):
        return "下跌"
    if normalize_trade_direction(direction) == "short" and _has_any(text, ["爆仓", "强平", "穿仓"]):
        return "上涨"
    return None


def analyze_review_outcome(text: str, direction: str) -> Optional[Outcome]:
    normalized = normalize_trade_direction(direction)
    patterns = SHORT_OUTCOMES if normalized == "short" else LONG_OUTCOMES
    preferred = _preferred_market(text, normalized)
    if preferred:
        patterns = sorted(patterns, key=lambda item: 0 if item["market"] == preferred else 1)
    for pattern in patterns:
        if _has_any(text, pattern["keywords"]):  # type: ignore[arg-type]
            return {
                "market": str(pattern["market"]),
                "behavior": str(pattern["behavior"]),
                "mistake": str(pattern["mistake"]),
                "lesson": str(pattern["lesson"]),
                "next_action": str(pattern["next_action"]),
            }
    return None


def outcome_rehearsal(direction: str) -> str:
    normalized = normalize_trade_direction(direction)
    if normalized == "short":
        return "做空后只会遇到三类结果：跌了、横盘、涨了。真正要提前写的是：跌了怎么止盈，横盘多久平仓，涨了多少认错。"
    if normalized == "watch":
        return "观察不是空等。你要提前写清楚：什么信号出现才行动，什么风险确认就继续不碰。"
    return "做多后只会遇到三类结果：涨了、横盘、跌了。真正要提前写的是：涨了怎么处理，横盘等多久，跌了哪里退出。"
