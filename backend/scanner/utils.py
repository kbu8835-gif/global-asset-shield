def clamp_score(score: int) -> int:
    return max(0, min(100, int(score)))


def risk_level(score: int) -> str:
    score = clamp_score(score)
    if score <= 30:
        return "低风险"
    if score <= 60:
        return "中风险"
    if score <= 80:
        return "高风险"
    return "极高风险"

