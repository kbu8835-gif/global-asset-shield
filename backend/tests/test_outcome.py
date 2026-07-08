from immune.outcome import analyze_review_outcome, outcome_rehearsal


def test_long_outcome_understands_paraphrases():
    sold_early = analyze_review_outcome("我刚提前止盈，后面马上继续拉升，感觉卖早了", "long")
    assert sold_early is not None
    assert sold_early["mistake"] == "提前卖飞"

    impatient = analyze_review_outcome("横盘磨了很久，我失去耐心就清仓了", "long")
    assert impatient is not None
    assert impatient["mistake"] == "横盘失去耐心"

    average_down = analyze_review_outcome("后来跌了，我越跌越买，想把成本摊平", "long")
    assert average_down is not None
    assert average_down["mistake"] == "下跌补仓"

    liquidation = analyze_review_outcome("用了杠杆，最后被强平了", "long")
    assert liquidation is not None
    assert liquidation["mistake"] == "杠杆爆仓"


def test_short_outcome_understands_paraphrases():
    early_profit = analyze_review_outcome("空单平早了，刚平后价格继续下跌", "short")
    assert early_profit is not None
    assert early_profit["mistake"] == "做空提前止盈"

    add_short = analyze_review_outcome("上涨后我又加了空，结果越亏越多", "short")
    assert add_short is not None
    assert add_short["mistake"] == "逆势补空"

    stop_loss = analyze_review_outcome("行情反弹，我按计划平空止损", "short")
    assert stop_loss is not None
    assert stop_loss["mistake"] == "做空按计划止损"

    liquidation = analyze_review_outcome("空单没止损，最后爆仓", "short")
    assert liquidation is not None
    assert liquidation["mistake"] == "做空爆仓"


def test_outcome_rehearsal_is_direction_specific():
    assert "涨了、横盘、跌了" in outcome_rehearsal("long")
    assert "跌了、横盘、涨了" in outcome_rehearsal("short")
