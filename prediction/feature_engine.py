import math
import statistics
from collections import defaultdict


MIN_HISTORY = 20


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5:
        code = code[:4]

    return code


def num(value):
    if value is None:
        return None

    try:
        value = float(value)

        if math.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def pct_change(new, old):
    if new is None or old in (None, 0):
        return None

    return (new / old - 1.0) * 100.0


def safe_stdev(values):
    values = [
        v for v in values
        if v is not None
    ]

    if len(values) < 2:
        return None

    return statistics.stdev(values)


def ratio(value, base):
    if value is None or base in (None, 0):
        return None

    return value / base


def complete_mean(values, required_count):
    if len(values) < required_count:
        return None

    if any(
        value is None
        for value in values
    ):
        return None

    return statistics.mean(values)


def raw_row_to_record(row):
    """
    Convert one cached J-Quants row into the canonical
    v5.11 feature-engine record.
    """

    return {
        "date": row.get("Date"),

        # Raw prices:
        # Used for actual execution / gap calculations.
        "open": num(row.get("O")),
        "high": num(row.get("H")),
        "low": num(row.get("L")),
        "close": num(row.get("C")),
        "volume": num(row.get("Vo")),
        "trading_value": num(row.get("Va")),

        # Adjusted prices:
        # Used for historical price factors.
        "adj_open": num(row.get("AdjO")),
        "adj_high": num(row.get("AdjH")),
        "adj_low": num(row.get("AdjL")),
        "adj_close": num(row.get("AdjC")),
        "adj_volume": num(row.get("AdjVo")),

        "market_cap": num(row.get("MktCap")),
        "upper_limit": num(row.get("UL")),
        "lower_limit": num(row.get("LL")),
    }


def build_stock_history(payloads):
    """
    payloads:
        iterable containing cached J-Quants JSON payloads.

    Returns:
        dict[code] -> chronological list of canonical records
    """

    stocks = defaultdict(list)

    for payload in payloads:

        if isinstance(payload, dict):
            rows = payload.get("rows", [])
        else:
            rows = payload

        for row in rows:

            code = normalize_code(
                row.get("Code")
            )

            if not code:
                continue

            stocks[code].append(
                raw_row_to_record(row)
            )

    for code in stocks:
        stocks[code].sort(
            key=lambda x: x["date"] or ""
        )

    return stocks


def historical_return(rows, days):
    if len(rows) <= days:
        return None

    current = rows[-1]["adj_close"]
    past = rows[-1 - days]["adj_close"]

    return pct_change(
        current,
        past
    )


def volatility(rows, window):
    if len(rows) < window + 1:
        return None

    selected = rows[-(window + 1):]

    returns = []

    for i in range(1, len(selected)):

        value = pct_change(
            selected[i]["adj_close"],
            selected[i - 1]["adj_close"],
        )

        if value is not None:
            returns.append(value)

    # Require the complete return window.
    if len(returns) != window:
        return None

    return safe_stdev(
        returns
    )


def high_distance(rows, window):
    if len(rows) < window:
        return None

    selected = rows[-window:]

    current = rows[-1]["adj_close"]

    highs = [
        r["adj_high"]
        for r in selected
        if r["adj_high"] is not None
    ]

    if (
        current is None
        or len(highs) != window
    ):
        return None

    highest = max(highs)

    return pct_change(
        current,
        highest
    )


def consecutive_up_days(rows):
    if len(rows) < 2:
        return 0

    count = 0

    for i in range(
        len(rows) - 1,
        0,
        -1,
    ):

        current = rows[i]["adj_close"]
        previous = rows[i - 1]["adj_close"]

        if (
            current is None
            or previous is None
        ):
            break

        if current > previous:
            count += 1
        else:
            break

    return count


def calculate_stock(code, rows):
    """
    Single source of truth for v5.11 price-factor calculation.

    IMPORTANT:
    rows must contain only information available on or before
    the requested feature date.
    """

    if not rows:
        return None

    current = rows[-1]

    current_volume = current["adj_volume"]
    current_value = current["trading_value"]

    previous = rows[:-1]

    volume_5_base = complete_mean(
        [
            r["adj_volume"]
            for r in previous[-5:]
        ],
        5,
    )

    volume_20_base = complete_mean(
        [
            r["adj_volume"]
            for r in previous[-20:]
        ],
        20,
    )

    value_5_base = complete_mean(
        [
            r["trading_value"]
            for r in previous[-5:]
        ],
        5,
    )

    value_20_base = complete_mean(
        [
            r["trading_value"]
            for r in previous[-20:]
        ],
        20,
    )

    gap = None

    if len(rows) >= 2:
        gap = pct_change(
            current["open"],
            rows[-2]["close"],
        )

    return {
        "code": code,
        "feature_date": current["date"],
        "history_days": len(rows),

        "previous_close": current["close"],
        "market_cap": current["market_cap"],

        # Momentum
        "return_1d": historical_return(rows, 1),
        "return_5d": historical_return(rows, 5),
        "return_10d": historical_return(rows, 10),
        "return_20d": historical_return(rows, 20),
        "return_60d": historical_return(rows, 60),

        # Flow
        "volume": current_volume,

        "volume_ratio_5d": ratio(
            current_volume,
            volume_5_base,
        ),

        "volume_ratio_20d": ratio(
            current_volume,
            volume_20_base,
        ),

        "trading_value": current_value,

        "trading_value_ratio_5d": ratio(
            current_value,
            value_5_base,
        ),

        "trading_value_ratio_20d": ratio(
            current_value,
            value_20_base,
        ),

        # Risk / price structure
        "volatility_5d": volatility(
            rows,
            5,
        ),

        "volatility_20d": volatility(
            rows,
            20,
        ),

        "distance_from_20d_high": high_distance(
            rows,
            20,
        ),

        "distance_from_60d_high": high_distance(
            rows,
            60,
        ),

        "consecutive_up_days": consecutive_up_days(
            rows
        ),

        # Raw execution price relationship
        "gap": gap,

        "upper_limit": current["upper_limit"],
        "lower_limit": current["lower_limit"],

        "source": "J-Quants",
        "feature_version":
            "v511-price-factor-v2-common",
    }
