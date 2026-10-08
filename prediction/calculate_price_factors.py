import json
import sys
from pathlib import Path

from feature_engine import (
    MIN_HISTORY,
    build_stock_history,
    calculate_stock,
)


DATA_DIR = Path("data/market/jquants")
OUTPUT_DIR = Path("data/features")


def log(*args):
    print(*args, flush=True)


def load_history():

    files = sorted(
        DATA_DIR.glob("????-??-??.json")
    )

    if not files:
        raise RuntimeError(
            "No J-Quants history files"
        )

    payloads = []

    for file in files:

        payloads.append(
            json.loads(
                file.read_text(
                    encoding="utf-8"
                )
            )
        )

    return build_stock_history(
        payloads
    )


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

        result = calculate_stock(
            code,
            rows,
        )

        if result is None:
            insufficient += 1
            continue

        features.append(result)

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
            "v511-price-factor-v2-common",

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
        "Feature version:",
        "v511-price-factor-v2-common"
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
