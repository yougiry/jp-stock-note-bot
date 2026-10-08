import json
import sys
from pathlib import Path

from collect_universe import collect_jpx_universe


FEATURE_DIR = Path("data/features")
OUTPUT_DIR = Path("data/universe")

MIN_COVERAGE = 0.90


def log(*args):
    print(*args, flush=True)


def fail(message, code=1):
    log("")
    log("==============================")
    log("UNIVERSE FEATURES: FAILED")
    log(message)
    log("==============================")
    sys.exit(code)


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5:
        code = code[:4]

    return code


def find_latest_feature_file():

    files = sorted(
        FEATURE_DIR.glob(
            "price_factors_????-??-??.json"
        )
    )

    if not files:
        fail(
            "Price factor file not found"
        )

    return files[-1]


def main():

    log("")
    log("==============================")
    log("v5.11 UNIVERSE FEATURE BUILDER")
    log("==============================")

    # ----------------------------------
    # JPX Universe
    # ----------------------------------

    log("")
    log("Loading JPX Universe...")

    universe = collect_jpx_universe()

    if not universe:
        fail(
            "JPX Universe is empty"
        )

    universe_map = {}

    for stock in universe:

        code = normalize_code(
            stock["code"]
        )

        if not code:
            continue

        universe_map[code] = {
            "code": code,
            "name": stock["name"],
            "market": stock["market"],
        }

    log(
        "JPX Universe:",
        len(universe_map)
    )

    # ----------------------------------
    # Price Factors
    # ----------------------------------

    feature_file = (
        find_latest_feature_file()
    )

    log(
        "Feature file:",
        feature_file
    )

    payload = json.loads(
        feature_file.read_text(
            encoding="utf-8"
        )
    )

    features = payload.get(
        "features",
        []
    )

    if not features:
        fail(
            "Feature data is empty"
        )

    feature_map = {}

    for feature in features:

        code = normalize_code(
            feature.get("code")
        )

        if code:
            feature_map[code] = feature

    log(
        "Price Factors:",
        len(feature_map)
    )

    # ----------------------------------
    # JOIN
    # ----------------------------------

    joined = []
    missing = []

    for code, stock in universe_map.items():

        feature = feature_map.get(
            code
        )

        if feature is None:

            missing.append(
                stock
            )

            continue

        item = {
            **stock,
            **feature,
        }

        joined.append(
            item
        )

    universe_count = len(
        universe_map
    )

    matched_count = len(
        joined
    )

    missing_count = len(
        missing
    )

    coverage = (
        matched_count /
        universe_count
        if universe_count
        else 0
    )

    # ----------------------------------
    # Report
    # ----------------------------------

    log("")
    log("==============================")
    log("UNIVERSE COVERAGE")
    log("==============================")

    log(
        "JPX Universe:",
        universe_count
    )

    log(
        "Price Factors:",
        len(feature_map)
    )

    log(
        "Matched:",
        matched_count
    )

    log(
        "Missing:",
        missing_count
    )

    log(
        "Coverage:",
        f"{coverage * 100:.2f}%"
    )

    if missing:

        log("")
        log("Missing sample:")

        for stock in missing[:30]:

            log(
                stock["code"],
                stock["name"],
                stock["market"],
            )

    # ----------------------------------
    # Coverage Gate
    # ----------------------------------

    if coverage < MIN_COVERAGE:

        fail(
            f"Coverage "
            f"{coverage * 100:.2f}% "
            f"< "
            f"{MIN_COVERAGE * 100:.0f}%",
            code=2,
        )

    # ----------------------------------
    # Output
    # ----------------------------------

    joined.sort(
        key=lambda x: x["code"]
    )

    feature_date = payload.get(
        "feature_date"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR /
        f"v511_universe_{feature_date}.json"
    )

    result = {
        "feature_date":
            feature_date,

        "schema":
            "v511-universe-feature-v1",

        "universe_source":
            "JPX",

        "price_source":
            "J-Quants",

        "universe_count":
            universe_count,

        "matched_count":
            matched_count,

        "missing_count":
            missing_count,

        "coverage":
            coverage,

        "stocks":
            joined,
    }

    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log("")
    log("==============================")
    log("UNIVERSE FEATURES: PASS")
    log("==============================")

    log(
        "Output:",
        output
    )

    log("")
    log("SAMPLE:")

    for item in joined[:3]:

        log({
            "code":
                item["code"],

            "name":
                item["name"],

            "market":
                item["market"],

            "close":
                item.get(
                    "previous_close"
                ),

            "return_5d":
                item.get(
                    "return_5d"
                ),

            "volume_ratio_5d":
                item.get(
                    "volume_ratio_5d"
                ),

            "market_cap":
                item.get(
                    "market_cap"
                ),
        })


if __name__ == "__main__":
    main()
