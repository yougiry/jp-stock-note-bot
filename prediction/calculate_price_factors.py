import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


DATA_DIR = Path("data/market/jquants")
OUTPUT_DIR = Path("data/features")

MIN_HISTORY = 20


def log(*args):
    print(*args, flush=True)


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    # J-Quants v2 -> JPX 4-character code
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


def safe_mean(values):
    values = [
        v for v in values
        if v is not None
    ]

    if not values:
        return None

    return statistics.mean(values)


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


def load_history():

    files = sorted(
        DATA_DIR.glob("????-??-??.json")
    )

    if not files:
        raise RuntimeError(
            "No J-Quants history files"
        )

    stocks = defaultdict(list)

    for file in files:

        payload = json.loads(
            file.read_text(
                encoding="utf-8"
            )
        )

        rows = payload.get("rows", [])

        for row in rows:

            code = normalize_code(
                row.get("Code")
            )

            if not code:
                continue

            record = {
                "date":
                    row.get("Date"),

                "open":
                    num(row.get("O")),

                "high":
                    num(row.get("H")),

                "low":
                    num(row.get("L")),

                "close":
                    num(row.get("C")),

                "volume":
                    num(row.get("Vo")),

                "trading_value":
                    num(row.get("Va")),

                "adj_open":
                    num(row.get("AdjO")),

                "adj_high":
                    num(row.get("AdjH")),

                "adj_low":
                    num(row.get("AdjL")),

                "adj_close":
                    num(row.get("AdjC")),

                "adj_volume":
                    num(row.get("AdjVo")),

                "market_cap":
                    num(row.get("MktCap")),

                "upper_limit":
                    num(row.get("UL")),

                "lower_limit":
                    num(row.get("LL")),
            }

            stocks[code].append(record)

    for code in stocks:
        stocks[code].sort(
            key=lambda x: x["date"]
        )

    return stocks


def historical_return(rows, days):

    # Current day versus N trading observations ago.
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

    for i in range(
        1,
        len(selected)
    ):

        value = pct_change(
            selected[i]["adj_close"],
            selected[i - 1]["adj_close"],
        )

        if value is not None:
            returns.append(value)

    return safe_stdev(
        returns
    )


def high_distance(rows, window):

    if not rows:
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
        or not highs
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


def calculate_stock(
    code,
    rows,
):

    current = rows[-1]

    current_volume = (
        current["adj_volume"]
    )

    current_value = (
        current["trading_value"]
    )

    # Previous observations only.
    # Current day is deliberately excluded
    # from baseline averages.
    previous = rows[:-1]

    volume_5_base = safe_mean([
        r["adj_volume"]
        for r in previous[-5:]
    ])

    volume_20_base = safe_mean([
        r["adj_volume"]
        for r in previous[-20:]
    ])

    value_5_base = safe_mean([
        r["trading_value"]
        for r in previous[-5:]
    ])

    value_20_base = safe_mean([
        r["trading_value"]
        for r in previous[-20:]
    ])

    gap = None

    if len(rows) >= 2:
        gap = pct_change(
            current["open"],
            rows[-2]["close"],
        )

    result = {
        "code":
            code,

        "feature_date":
            current["date"],

        "history_days":
            len(rows),

        "previous_close":
            current["close"],

        "market_cap":
            current["market_cap"],

        # Momentum
        "return_1d":
            historical_return(rows, 1),

        "return_5d":
            historical_return(rows, 5),

        "return_10d":
            historical_return(rows, 10),

        "return_20d":
            historical_return(rows, 20),

        "return_60d":
            historical_return(rows, 60),

        # Flow
        "volume":
            current_volume,

        "volume_ratio_5d":
            ratio(
                current_volume,
                volume_5_base,
            ),

        "volume_ratio_20d":
            ratio(
                current_volume,
                volume_20_base,
            ),

        "trading_value":
            current_value,

        "trading_value_ratio_5d":
            ratio(
                current_value,
                value_5_base,
            ),

        "trading_value_ratio_20d":
            ratio(
                current_value,
                value_20_base,
            ),

        # Risk / price structure
        "volatility_5d":
            volatility(rows, 5),

        "volatility_20d":
            volatility(rows, 20),

        "distance_from_20d_high":
            high_distance(rows, 20),

        "distance_from_60d_high":
            high_distance(rows, 60),

        "consecutive_up_days":
            consecutive_up_days(rows),

        "gap":
            gap,

        "upper_limit":
            current["upper_limit"],

        "lower_limit":
            current["lower_limit"],

        "source":
            "J-Quants",

        "feature_version":
            "v511-price-factor-v1",
    }

    return result


def main():

    log("")
    log("==============================")
    log("v5.11 PRICE FACTOR ENGINE")
    log("==============================")

    stocks = load_history()

    log(
        "Stocks loaded:",
        len(stocks)
    )

    features = []

    insufficient = 0

    for code, rows in stocks.items():

        if len(rows) < MIN_HISTORY:
            insufficient += 1
            continue

        features.append(
            calculate_stock(
                code,
                rows,
            )
        )

    features.sort(
        key=lambda x: x["code"]
    )

    log(
        "Feature stocks:",
        len(features)
    )

    log(
        "Insufficient history:",
        insufficient
    )

    if not features:

        log("")
        log(
            "FEATURE STATUS: PARTIAL"
        )

        log(
            f"Need at least {MIN_HISTORY} "
            "trading days."
        )

        # Not a system failure.
        sys.exit(0)

    feature_date = max(
        f["feature_date"]
        for f in features
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR /
        f"price_factors_{feature_date}.json"
    )

    payload = {
        "feature_date":
            feature_date,

        "feature_version":
            "v511-price-factor-v1",

        "source":
            "J-Quants",

        "stock_count":
            len(features),

        "features":
            features,
    }

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log("")
    log("==============================")
    log("PRICE FACTOR ENGINE: PASS")
    log("==============================")

    log(
        "Feature date:",
        feature_date
    )

    log(
        "Stocks:",
        len(features)
    )

    log(
        "Output:",
        output
    )

    log("")
    log("SAMPLE:")

    for item in features[:3]:
        log(item)


if __name__ == "__main__":
    main()
