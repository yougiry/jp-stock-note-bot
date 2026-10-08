import json
import math
import sys
from pathlib import Path

from feature_engine import (
    build_stock_history,
    calculate_stock,
)

from market_score import (
    SCORE_VERSION,
    calculate_market_score,
)


RAW_DIR = Path("data/market/jquants")
FEATURE_DIR = Path("data/features")

TOLERANCE = 1e-9

FIELDS = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "volume_ratio_5d",
    "volume_ratio_20d",
    "trading_value_ratio_5d",
    "trading_value_ratio_20d",
    "volatility_5d",
    "volatility_20d",
    "distance_from_20d_high",
    "distance_from_60d_high",
    "consecutive_up_days",
    "gap",
    "market_cap",
    "trading_value",
]


def log(*args):
    print(*args, flush=True)


def same_value(a, b):

    if a is None and b is None:
        return True

    if a is None or b is None:
        return False

    if isinstance(a, (int, float)) and isinstance(
        b,
        (int, float),
    ):
        return math.isclose(
            float(a),
            float(b),
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE,
        )

    return a == b


def latest_feature_file():

    files = sorted(
        FEATURE_DIR.glob(
            "price_factors_????-??-??.json"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Price factor file not found"
        )

    return files[-1]


def load_raw_history_until(feature_date):

    payloads = []

    for path in sorted(
        RAW_DIR.glob("????-??-??.json")
    ):

        if path.stem > feature_date:
            continue

        payloads.append(
            json.loads(
                path.read_text(
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
    log("v5.11 ENGINE PARITY TEST")
    log("==============================")

    feature_file = latest_feature_file()

    payload = json.loads(
        feature_file.read_text(
            encoding="utf-8"
        )
    )

    feature_date = payload.get(
        "feature_date"
    )

    saved_features = {
        item["code"]: item
        for item in payload.get(
            "features",
            []
        )
    }

    if not feature_date:
        log("FAIL: feature_date missing")
        sys.exit(1)

    if not saved_features:
        log("FAIL: saved features empty")
        sys.exit(1)

    log(
        "Feature date:",
        feature_date
    )

    log(
        "Score version:",
        SCORE_VERSION
    )

    stocks = load_raw_history_until(
        feature_date
    )

    checked = 0
    mismatches = []

    for code, saved in saved_features.items():

        rows = stocks.get(
            code
        )

        if not rows:
            mismatches.append(
                {
                    "code": code,
                    "field": "history",
                    "saved": "exists",
                    "recalculated": None,
                }
            )
            continue

        recalculated = calculate_stock(
            code,
            rows,
        )

        if recalculated is None:
            mismatches.append(
                {
                    "code": code,
                    "field": "calculate_stock",
                    "saved": "exists",
                    "recalculated": None,
                }
            )
            continue

        for field in FIELDS:

            a = saved.get(
                field
            )

            b = recalculated.get(
                field
            )

            if not same_value(a, b):

                mismatches.append(
                    {
                        "code": code,
                        "field": field,
                        "saved": a,
                        "recalculated": b,
                    }
                )

        # Score both representations.
        saved_score = calculate_market_score(
            saved
        )

        recalculated_score = calculate_market_score(
            recalculated
        )

        for field in [
            "price_score",
            "flow_score",
            "liquidity_score",
            "risk_quality_score",
            "size_score",
            "technical_score",
        ]:

            a = saved_score.get(
                field
            )

            b = recalculated_score.get(
                field
            )

            if not same_value(a, b):

                mismatches.append(
                    {
                        "code": code,
                        "field":
                            f"score.{field}",
                        "saved": a,
                        "recalculated": b,
                    }
                )

        checked += 1

    log(
        "Stocks checked:",
        checked
    )

    log(
        "Mismatches:",
        len(mismatches)
    )

    if mismatches:

        log("")
        log("MISMATCH SAMPLE:")

        for item in mismatches[:20]:
            log(item)

        log("")
        log("==============================")
        log("ENGINE PARITY TEST: FAIL")
        log("==============================")

        sys.exit(1)

    log("")
    log("==============================")
    log("ENGINE PARITY TEST: PASS")
    log("==============================")

    log(
        "Feature parity: PASS"
    )

    log(
        "Score parity: PASS"
    )

    log(
        "Feature date:",
        feature_date
    )

    log(
        "Stocks verified:",
        checked
    )

    log(
        "Score version:",
        SCORE_VERSION
    )


if __name__ == "__main__":
    main()
