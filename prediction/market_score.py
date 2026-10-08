import math


SCORE_VERSION = "v511-market-score-v1"


def clamp(value, low, high):
    if value is None:
        return None
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if math.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


# ======================================
# PRICE MOMENTUM
# 0 - 25
# ======================================

def score_price(stock):

    score = 0.0

    r1 = safe_float(stock.get("return_1d"))
    r5 = safe_float(stock.get("return_5d"))
    r20 = safe_float(stock.get("return_20d"))
    high20 = safe_float(
        stock.get("distance_from_20d_high")
    )

    if r1 is not None:
        if 1 <= r1 <= 5:
            score += 5
        elif 0 < r1 < 1:
            score += 2
        elif 5 < r1 <= 10:
            score += 3
        elif r1 < -3:
            score -= 3

    if r5 is not None:
        if 2 <= r5 <= 12:
            score += 7
        elif 0 < r5 < 2:
            score += 3
        elif 12 < r5 <= 20:
            score += 4
        elif r5 > 20:
            score -= 2

    if r20 is not None:
        if 3 <= r20 <= 20:
            score += 6
        elif 0 < r20 < 3:
            score += 2
        elif 20 < r20 <= 35:
            score += 3
        elif r20 > 35:
            score -= 2

    if high20 is not None:
        if -3 <= high20 <= 0:
            score += 7
        elif -7 <= high20 < -3:
            score += 4
        elif high20 < -15:
            score -= 2

    return clamp(score, 0, 25)


# ======================================
# FLOW
# 0 - 25
# ======================================

def score_flow(stock):

    score = 0.0

    vr5 = safe_float(
        stock.get("volume_ratio_5d")
    )
    vr20 = safe_float(
        stock.get("volume_ratio_20d")
    )
    tvr5 = safe_float(
        stock.get("trading_value_ratio_5d")
    )
    tvr20 = safe_float(
        stock.get("trading_value_ratio_20d")
    )

    if vr5 is not None:
        if 1.5 <= vr5 < 3:
            score += 7
        elif 3 <= vr5 < 6:
            score += 9
        elif vr5 >= 6:
            score += 6
        elif vr5 < 0.5:
            score -= 2

    if vr20 is not None:
        if 1.3 <= vr20 < 3:
            score += 5
        elif vr20 >= 3:
            score += 6

    if tvr5 is not None:
        if 1.5 <= tvr5 < 3:
            score += 5
        elif 3 <= tvr5 < 6:
            score += 7
        elif tvr5 >= 6:
            score += 5

    if tvr20 is not None:
        if 1.3 <= tvr20:
            score += 3

    return clamp(score, 0, 25)


# ======================================
# LIQUIDITY / EXECUTION
# 0 - 20
# ======================================

def score_liquidity(stock):

    value = safe_float(
        stock.get("trading_value")
    )

    if value is None:
        return 0

    if value >= 1_000_000_000:
        return 20

    if value >= 500_000_000:
        return 17

    if value >= 100_000_000:
        return 13

    if value >= 30_000_000:
        return 8

    if value >= 10_000_000:
        return 4

    return 0


# ======================================
# RISK QUALITY
# 0 - 20
# ======================================

def score_risk(stock):

    score = 20.0

    vol20 = safe_float(
        stock.get("volatility_20d")
    )
    gap = safe_float(
        stock.get("gap")
    )
    r1 = safe_float(
        stock.get("return_1d")
    )

    if vol20 is not None:
        if vol20 > 8:
            score -= 10
        elif vol20 > 5:
            score -= 6
        elif vol20 > 3:
            score -= 3

    if gap is not None:
        if abs(gap) > 15:
            score -= 8
        elif abs(gap) > 10:
            score -= 5
        elif abs(gap) > 5:
            score -= 2

    if r1 is not None:
        if r1 > 15:
            score -= 5
        elif r1 < -10:
            score -= 5

    return clamp(score, 0, 20)


# ======================================
# CAPITAL / SIZE
# 0 - 10
# ======================================

def score_size(stock):

    cap = safe_float(
        stock.get("market_cap")
    )

    if cap is None:
        return 0

    if 10_000 <= cap < 100_000:
        return 10

    if 100_000 <= cap < 300_000:
        return 8

    if 300_000 <= cap < 1_000_000:
        return 5

    if cap >= 1_000_000:
        return 2

    return 3


def calculate_market_score(stock):

    price = score_price(stock)
    flow = score_flow(stock)
    liquidity = score_liquidity(stock)
    risk = score_risk(stock)
    size = score_size(stock)

    total = (
        price
        + flow
        + liquidity
        + risk
        + size
    )

    return {
        "price_score": price,
        "flow_score": flow,
        "liquidity_score": liquidity,
        "risk_quality_score": risk,
        "size_score": size,
        "technical_score": total,
        "score_version": SCORE_VERSION,
    }


def ranking_sort_key(stock):

    return (
        stock["technical_score"],
        stock["flow_score"],
        stock["price_score"],
        stock["liquidity_score"],
    )
