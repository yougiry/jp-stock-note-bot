import json
from pathlib import Path
from collections import defaultdict


RAW_DIR = Path("data/market/jquants")
OUTPUT_DIR = Path("data/labels")


def log(*args):
    print(*args, flush=True)


def num(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5:
        code = code[:4]

    return code


def pct(value, base):
    if value is None or base is None:
        return None

    if base == 0:
        return None

    return ((value / base) - 1) * 100


def load_history():

    by_date = {}

    files = sorted(
        RAW_DIR.glob("????-??-??.json")
    )

    for path in files:

        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

        # Support either raw list or {"data": [...]}
        if isinstance(payload, dict):
            rows = payload.get("data", [])
        else:
            rows = payload

        date_map = {}

        for row in rows:

            code = normalize_code(
                row.get("Code")
            )

            if not code:
                continue

            date_map[code] = {
                "open": num(row.get("O")),
                "high": num(row.get("H")),
                "low": num(row.get("L")),
                "close": num(row.get("C")),
                "volume": num(row.get("Vo")),
                "trading_value": num(row.get("Va")),
            }

        if date_map:
            by_date[path.stem] = date_map

    return by_date


def build_label(
    feature_date,
    label_date,
    code,
    row,
):

    open_price = row["open"]
    high = row["high"]
    low = row["low"]
    close = row["close"]

    valid_open = (
        open_price is not None
        and open_price > 0
    )

    if not valid_open:
        return {
            "code": code,
            "feature_date": feature_date,
            "label_date": label_date,
            "valid_open": False,
            "no_open": True,
        }

    mfe = pct(high, open_price)
    mae = pct(low, open_price)
    close_return = pct(close, open_price)

    hit_plus_3 = (
        mfe is not None and mfe >= 3
    )

    hit_plus_5 = (
        mfe is not None and mfe >= 5
    )

    hit_plus_10 = (
        mfe is not None and mfe >= 10
    )

    hit_minus_3 = (
        mae is not None and mae <= -3
    )

    hit_minus_5 = (
        mae is not None and mae <= -5
    )

    # Standard benchmark:
    # Buy at open.
    # If intraday low reaches -3%, assume
    # the stop is executed at -3%.
    # Otherwise exit at close.
    #
    # This is a benchmark approximation,
    # not an exact fill/slippage model.
    if hit_minus_3:
        benchmark_return = -3.0
        benchmark_exit = "STOP_-3"
    else:
        benchmark_return = close_return
        benchmark_exit = "CLOSE"

    # Daily OHLC cannot establish which
    # threshold was hit first when both
    # target and stop are reached.
    if hit_plus_3 and hit_minus_3:
        plus3_stop3_order = "AMBIGUOUS"
    elif hit_plus_3:
        plus3_stop3_order = "TARGET_ONLY"
    elif hit_minus_3:
        plus3_stop3_order = "STOP_ONLY"
    else:
        plus3_stop3_order = "NEITHER"

    if hit_plus_5 and hit_minus_3:
        plus5_stop3_order = "AMBIGUOUS"
    elif hit_plus_5:
        plus5_stop3_order = "TARGET_ONLY"
    elif hit_minus_3:
        plus5_stop3_order = "STOP_ONLY"
    else:
        plus5_stop3_order = "NEITHER"

    return {
        "code": code,

        "feature_date": feature_date,
        "label_date": label_date,

        "valid_open": True,
        "no_open": False,

        "open": open_price,
        "high": high,
        "low": low,
        "close": close,

        "volume": row["volume"],
        "trading_value": row["trading_value"],

        "mfe_pct": mfe,
        "mae_pct": mae,
        "open_to_close_pct": close_return,

        "hit_plus_3": hit_plus_3,
        "hit_plus_5": hit_plus_5,
        "hit_plus_10": hit_plus_10,

        "hit_minus_3": hit_minus_3,
        "hit_minus_5": hit_minus_5,

        "benchmark_return_pct":
            benchmark_return,

        "benchmark_exit":
            benchmark_exit,

        "plus3_stop3_order":
            plus3_stop3_order,

        "plus5_stop3_order":
            plus5_stop3_order,
    }


def main():

    log("")
    log("==============================")
    log("v5.11 NEXT-DAY LABEL BUILDER")
    log("==============================")

    history = load_history()

    dates = sorted(history.keys())

    log("Trading days:", len(dates))

    if len(dates) < 2:
        log("NO-RUN: insufficient history")
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_labels = 0
    valid_labels = 0
    no_open = 0

    summary = []

    for i in range(len(dates) - 1):

        feature_date = dates[i]
        label_date = dates[i + 1]

        next_day = history[label_date]

        labels = []

        for code, row in next_day.items():

            label = build_label(
                feature_date,
                label_date,
                code,
                row,
            )

            labels.append(label)

            total_labels += 1

            if label["valid_open"]:
                valid_labels += 1
            else:
                no_open += 1

        output = (
            OUTPUT_DIR /
            f"next_day_{feature_date}.json"
        )

        result = {
            "schema":
                "v511-next-day-label-v1",

            "feature_date":
                feature_date,

            "label_date":
                label_date,

            "source":
                "J-Quants",

            "label_count":
                len(labels),

            "labels":
                labels,
        }

        output.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        summary.append({
            "feature_date": feature_date,
            "label_date": label_date,
            "labels": len(labels),
        })

    log("")
    log("==============================")
    log("LABEL BUILD RESULT")
    log("==============================")

    log(
        "Date pairs:",
        len(summary)
    )

    log(
        "Total labels:",
        total_labels
    )

    log(
        "Valid open:",
        valid_labels
    )

    log(
        "No open:",
        no_open
    )

    if summary:
        log("")
        log(
            "First pair:",
            summary[0]
        )

        log(
            "Last pair:",
            summary[-1]
        )

    log("")
    log("==============================")
    log("NEXT-DAY LABEL BUILDER: PASS")
    log("==============================")


if __name__ == "__main__":
    main()
