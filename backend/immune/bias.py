from scanner.utils import clamp_score


BIAS_RULES = [
    {
        "bias_type": "FOMO",
        "keywords": ["怕踏空", "错过", "涨很多", "起飞", "再不上车"],
        "warning": "你现在可能不是在研究机会，而是在逃避错过的焦虑。",
        "better_question": "如果明天跌 30%，我还愿意按原计划持有吗？",
    },
    {
        "bias_type": "Sunk Cost",
        "keywords": ["亏了", "亏80%", "补仓", "回本", "舍不得割肉"],
        "warning": "你不是在补仓，你是在用更多钱证明自己没错。",
        "better_question": "如果我今天没有持仓，还会用同样价格买入吗？",
    },
    {
        "bias_type": "Confirmation Bias",
        "keywords": ["一定会涨", "必涨", "十倍", "百倍", "稳赚", "确定"],
        "warning": "你只在寻找支持上涨的证据，反对证据正在被你自动忽略。",
        "better_question": "我能否写出三个让我放弃买入的事实？",
    },
    {
        "bias_type": "Authority Bias",
        "keywords": ["KOL推荐", "大V说", "朋友说", "群里说", "老师说", "KOL"],
        "warning": "别人的影响力不是你的风控系统。",
        "better_question": "他披露了成本、仓位和卖出计划吗？",
    },
    {
        "bias_type": "Overconfidence",
        "keywords": ["我很确定", "闭眼买", "稳赚", "不会亏", "必跌", "一定会跌", "归零", "跌爆"],
        "warning": "越确定的时候，越要先问自己哪里可能错。",
        "better_question": "如果我判断错了，第一信号是什么？",
    },
    {
        "bias_type": "Revenge Trading",
        "keywords": ["回本", "翻回来", "上一单亏了", "这次一定", "报复", "干回来", "亏回来"],
        "warning": "你不是在交易机会，你是在和上一笔亏损较劲。",
        "better_question": "这笔交易独立来看仍然值得做吗？",
    },
    {
        "bias_type": "Short Bias",
        "keywords": ["做空", "开空", "short", "看跌", "跌爆", "归零"],
        "warning": "看空不等于可以做空。方向、时机和止损缺一项，做空会先惩罚你的仓位。",
        "better_question": "如果它先上涨 30%，我是否有明确止损，而不是加空证明自己？",
    },
    {
        "bias_type": "Lottery Bias",
        "keywords": ["十倍", "百倍", "暴富", "财富自由", "小买怡情搏一搏"],
        "warning": "彩票心理会让小概率收益看起来像计划。",
        "better_question": "如果它没有暴涨，我的普通情形收益从哪里来？",
    },
]


def detect_bias(text: str) -> dict:
    normalized = (text or "").replace(" ", "")
    biases = []
    for rule in BIAS_RULES:
        evidence = next((keyword for keyword in rule["keywords"] if keyword in normalized), None)
        if evidence:
            biases.append(
                {
                    "bias_type": rule["bias_type"],
                    "severity": "★★★★★",
                    "evidence": evidence,
                    "warning": rule["warning"],
                    "better_question": rule["better_question"],
                }
            )

    return {
        "bias_score": clamp_score(len(biases) * 20),
        "biases": biases,
    }
