import json
import math
from pathlib import Path
from statistics import mean

from feature_engine import (
    MIN_HISTORY,
    build_stock_history,
    calculate_stock,
)

from market_score import (
    SCORE_VERSION,
    calculate_market_score,
    ranking_sort_key,
)


RAW_DIR = Path("data/market/jquants")
LABEL_DIR = Path("data/labels")
OUTPUT_DIR = Path("data/backtest")

TOP_N = 30


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


def load_history():

    payloads_by_date = {}

    files = sorted(
        RAW_DIR.glob("????-??-??.json")
    )

    for path in files:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        payloads_by_date[
            path.stem
        ] = payload

    return payloads_by_date


def load_label(feature_date):

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


def avg(items, key):

    vals = [
        num(x.get(key))
        for x in items
        if num(x.get(key)) is not None
    ]

    return (
        mean(vals)
        if vals
        else None
    )


def rate(items, key):

    vals = [
        x.get(key)
        for x in items
        if x.get(key) is not None
    ]

    if not vals:
        return None

    return (
        sum(
            1
            for x in vals
            if x is True
        )
        / len(vals)
        * 100
    )


def report(name, items):

    log("")
    log("---", name, "---")

    log(
        "Samples:",
        len(items)
    )

    log(
        "Avg MFE:",
        round(
            avg(items, "mfe_pct"),
            3,
        )
    )

    log(
        "Avg MAE:",
        round(
            avg(items, "mae_pct"),
            3,
        )
    )

    log(
        "Avg Open->Close:",
        round(
            avg(
                items,
                "open_to_close_pct",
            ),
            3,
        )
    )

    log(
        "+3% rate:",
        round(
            rate(
                items,
                "hit_plus_3",
            ),
            2,
        )
    )

    log(
        "+5% rate:",
        round(
            rate(
                items,
                "hit_plus_5",
            ),
            2,
        )
    )

    log(
        "+10% rate:",
        round(
            rate(
                items,
                "hit_plus_10",
            ),
            2,
        )
    )

    log(
        "-3% rate:",
        round(
            rate(
                items,
                "hit_minus_3",
            ),
            2,
        )
    )

    log(
        "-5% rate:",
        round(
            rate(
                items,
                "hit_minus_5",
            ),
            2,
        )
    )

    log(
        "Benchmark return:",
        round(
            avg(
                items,
                "benchmark_return_pct",
            ),
            3,
        )
    )


def main():

    log("")
    log("==============================")
    log("v5.11 MARKET SCORE BACKTEST")
    log("==============================")

    log(
        "Feature engine:",
        "v511-price-factor-v2-common",
    )

    log(
        "Score version:",
        SCORE_VERSION,
    )

    history = load_history()

    dates = sorted(
        history
    )

    log(
        "Trading days:",
        len(dates)
    )

    results = []

    evaluated_dates = 0

    # Current feature day requires historical
    # information and a following label day.
    for date_index in range(
        MIN_HISTORY,
        len(dates) - 1,
    ):

        feature_date = (
            dates[date_index]
        )

        labels = load_label(
            feature_date
        )

        if not labels:
            continue

        # STRICT POINT-IN-TIME DATA:
        # Never use rows after feature_date.
        historical_payloads = [
            history[d]
            for d
            in dates[:date_index + 1]
        ]

        stocks = build_stock_history(
            historical_payloads
        )

        daily = []

        for code, rows in stocks.items():

            if len(rows) < MIN_HISTORY:
                continue

            # EXACT SAME FEATURE ENGINE
            # AS CURRENT RANKER PIPELINE.
            features = calculate_stock(
                code,
                rows,
            )

            if features is None:
                continue

            # EXACT SAME SCORE ENGINE
            # AS CURRENT RANKER.
            scores = calculate_market_score(
                features
            )

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

            item = {
                "code":
                    code,

                "feature_date":
                    feature_date,

                **scores,

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

                "hit_plus_10":
                    label.get(
                        "hit_plus_10"
                    ),

                "hit_minus_3":
                    label.get(
                        "hit_minus_3"
                    ),

                "hit_minus_5":
                    label.get(
                        "hit_minus_5"
                    ),

                "benchmark_return_pct":
                    label.get(
                        "benchmark_return_pct"
                    ),
            }

            daily.append(
                item
            )

        if not daily:
            continue

        # EXACT SAME TIE-BREAK AS
        # CURRENT MARKET RANKER.
        daily.sort(
            key=ranking_sort_key,
            reverse=True,
        )

        for rank, item in enumerate(
            daily,
            start=1,
        ):
            item["rank"] = rank

        results.extend(
            daily[:TOP_N]
        )

        evaluated_dates += 1

    if not results:

        log(
            "NO-RUN: no matched samples"
        )

        return

    top5 = [
        x
        for x in results
        if x["rank"] <= 5
    ]

    top10 = [
        x
        for x in results
        if x["rank"] <= 10
    ]

    top30 = results

    log(
        "Evaluated feature dates:",
        evaluated_dates,
    )

    report(
        "TOP 5",
        top5,
    )

    report(
        "TOP 10",
        top10,
    )

    report(
        "TOP 30",
        top30,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR
        / "market_score_backtest.json"
    )

    output.write_text(
        json.dumps(
            {
                "schema":
                    "v511-market-score-backtest-v2",

                "formal_prediction":
                    False,

                "backtest_status":
                    "PARTIAL-TEST",

                "feature_version":
                    "v511-price-factor-v2-common",

                "score_version":
                    SCORE_VERSION,

                "trading_days":
                    len(dates),

                "evaluated_feature_dates":
                    evaluated_dates,

                "top_n":
                    TOP_N,

                "samples":
                    results,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log("")
    log("==============================")
    log(
        "MARKET SCORE BACKTEST: PASS"
    )
    log("==============================")

    log(
        "Backtest status:",
        "PARTIAL-TEST"
    )

    log(
        "Feature version:",
        "v511-price-factor-v2-common"
    )

    log(
        "Score version:",
        SCORE_VERSION
    )

    log(
        "Output:",
        output
    )


if __name__ == "__main__":
    main()
