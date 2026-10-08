import json
import math
import sys
from pathlib import Path
from statistics import mean, median

from feature_engine import (
    build_stock_history,
    calculate_stock,
)


RAW_DIR = Path("data/market/jquants")
LABEL_DIR = Path("data/labels")

MIN_REQUIRED_DAYS = 61


def log(*args):
    print(*args, flush=True)


def num(value):
    try:
        if value is None:
            return None

        value = float(value)

        if math.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def normalize_code(value):

    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5:
        code = code[:4]

    return code


def avg(values):

    values = [
        v for v in values
        if v is not None
    ]

    return mean(values) if values else None


def med(values):

    values = [
        v for v in values
        if v is not None
    ]

    return median(values) if values else None


def load_history():

    result = {}

    for path in sorted(
        RAW_DIR.glob("????-??-??.json")
    ):

        result[path.stem] = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    return result


def load_labels(feature_date):

    path = (
        LABEL_DIR
        / f"next_day_{feature_date}.json"
    )

    if not path.exists():
        return {}

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return {
        normalize_code(x["code"]): x
        for x in payload.get(
            "labels",
            []
        )
    }


def summarize(name, samples):

    if not samples:
        return

    mfe = [
        num(x.get("mfe_pct"))
        for x in samples
    ]

    mae = [
        num(x.get("mae_pct"))
        for x in samples
    ]

    close = [
        num(x.get("open_to_close_pct"))
        for x in samples
    ]

    plus3 = [
        x.get("hit_plus_3")
        for x in samples
        if x.get("hit_plus_3") is not None
    ]

    minus3 = [
        x.get("hit_minus_3")
        for x in samples
        if x.get("hit_minus_3") is not None
    ]

    plus5 = [
        x.get("hit_plus_5")
        for x in samples
        if x.get("hit_plus_5") is not None
    ]

    minus5 = [
        x.get("hit_minus_5")
        for x in samples
        if x.get("hit_minus_5") is not None
    ]

    def hit_rate(values):
        if not values:
            return None

        return (
            sum(
                1
                for value in values
                if value is True
            )
            / len(values)
            * 100
        )

    log("")
    log("---", name, "---")

    log(
        "Samples:",
        len(samples)
    )

    log(
        "Avg MFE:",
        round(avg(mfe), 3)
    )

    log(
        "Median MFE:",
        round(med(mfe), 3)
    )

    log(
        "Avg MAE:",
        round(avg(mae), 3)
    )

    log(
        "Median MAE:",
        round(med(mae), 3)
    )

    log(
        "Avg Open->Close:",
        round(avg(close), 3)
    )

    log(
        "+3% rate:",
        round(hit_rate(plus3), 2)
    )

    log(
        "+5% rate:",
        round(hit_rate(plus5), 2)
    )

    log(
        "-3% rate:",
        round(hit_rate(minus3), 2)
    )

    log(
        "-5% rate:",
        round(hit_rate(minus5), 2)
    )


def main():

    log("")
    log("==============================")
    log("v5.11 60-DAY FACTOR ANALYSIS")
    log("==============================")

    history = load_history()

    dates = sorted(history)

    log(
        "Trading days:",
        len(dates)
    )

    if len(dates) < MIN_REQUIRED_DAYS:

        log(
            "NO-RUN: insufficient history"
        )

        log(
            "Required:",
            MIN_REQUIRED_DAYS
        )

        log(
            "Available:",
            len(dates)
        )

        sys.exit(0)

    samples = []

    # Start only once 60-day information
    # can exist.
    for date_index in range(
        60,
        len(dates) - 1,
    ):

        feature_date = dates[
            date_index
        ]

        labels = load_labels(
            feature_date
        )

        if not labels:
            continue

        payloads = [
            history[d]
            for d in dates[
                :date_index + 1
            ]
        ]

        stocks = build_stock_history(
            payloads
        )

        for code, rows in stocks.items():

            features = calculate_stock(
                code,
                rows
            )

            if features is None:
                continue

            r60 = num(
                features.get(
                    "return_60d"
                )
            )

            h60 = num(
                features.get(
                    "distance_from_60d_high"
                )
            )

            if (
                r60 is None
                or h60 is None
            ):
                continue

            label = labels.get(
                code
            )

            if (
                not label
                or not label.get(
                    "valid_open"
                )
            ):
                continue

            samples.append({
                "code":
                    code,

                "feature_date":
                    feature_date,

                "return_60d":
                    r60,

                "distance_from_60d_high":
                    h60,

                "mfe_pct":
                    label.get(
                        "mfe_pct"
                    ),

                "mae_pct":
                    label.get(
                        "mae_pct"
                    ),

                "open_to_close_pct":
                    label.get(
                        "open_to_close_pct"
                    ),

                "hit_plus_3":
                    label.get(
                        "hit_plus_3"
                    ),

                "hit_plus_5":
                    label.get(
                        "hit_plus_5"
                    ),

                "hit_minus_3":
                    label.get(
                        "hit_minus_3"
                    ),

                "hit_minus_5":
                    label.get(
                        "hit_minus_5"
                    ),
            })

    if not samples:

        log(
            "NO-RUN: no valid 60-day samples"
        )

        return

    log(
        "Valid samples:",
        len(samples)
    )

    # ----------------------------------
    # 60-DAY RETURN BUCKETS
    # ----------------------------------

    return_groups = {
        "R60 < -20%": [],
        "R60 -20% to 0%": [],
        "R60 0% to +20%": [],
        "R60 +20% to +50%": [],
        "R60 >= +50%": [],
    }

    for item in samples:

        value = item[
            "return_60d"
        ]

        if value < -20:
            key = "R60 < -20%"

        elif value < 0:
            key = "R60 -20% to 0%"

        elif value < 20:
            key = "R60 0% to +20%"

        elif value < 50:
            key = "R60 +20% to +50%"

        else:
            key = "R60 >= +50%"

        return_groups[key].append(
            item
        )

    log("")
    log("==============================")
    log("RETURN 60D BUCKETS")
    log("==============================")

    for name, group in (
        return_groups.items()
    ):
        summarize(
            name,
            group
        )

    # ----------------------------------
    # DISTANCE FROM 60-DAY HIGH
    # ----------------------------------

    high_groups = {
        "HIGH60 0% to -3%": [],
        "HIGH60 -3% to -7%": [],
        "HIGH60 -7% to -15%": [],
        "HIGH60 -15% to -30%": [],
        "HIGH60 below -30%": [],
    }

    for item in samples:

        value = item[
            "distance_from_60d_high"
        ]

        if value >= -3:
            key = "HIGH60 0% to -3%"

        elif value >= -7:
            key = "HIGH60 -3% to -7%"

        elif value >= -15:
            key = "HIGH60 -7% to -15%"

        elif value >= -30:
            key = "HIGH60 -15% to -30%"

        else:
            key = "HIGH60 below -30%"

        high_groups[key].append(
            item
        )

    log("")
    log("==============================")
    log("DISTANCE FROM 60D HIGH")
    log("==============================")

    for name, group in (
        high_groups.items()
    ):
        summarize(
            name,
            group
        )

    log("")
    log("==============================")
    log("60-DAY FACTOR ANALYSIS: PASS")
    log("==============================")

    log(
        "IMPORTANT:"
    )

    log(
        "This analysis does NOT modify "
        "market_score.py."
    )


if __name__ == "__main__":
    main()
