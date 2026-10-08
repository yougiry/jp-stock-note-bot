import json
import sys
from pathlib import Path

from market_score import (
    SCORE_VERSION,
    calculate_market_score,
    ranking_sort_key,
)


UNIVERSE_DIR = Path("data/universe")
OUTPUT_DIR = Path("data/ranking")

TOP_N = 30


def log(*args):
    print(*args, flush=True)


def latest_universe_file():

    files = sorted(
        UNIVERSE_DIR.glob(
            "v511_universe_????-??-??.json"
        )
    )

    if not files:
        raise FileNotFoundError(
            "Universe feature file not found"
        )

    return files[-1]


def main():

    log("")
    log("==============================")
    log("v5.11 MARKET CANDIDATE RANKER")
    log("==============================")

    source = latest_universe_file()

    log("Universe:", source)
    log("Score version:", SCORE_VERSION)

    payload = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    stocks = payload.get(
        "stocks",
        []
    )

    if not stocks:
        log("NO-RUN: Universe empty")
        sys.exit(2)

    ranked = []

    for stock in stocks:

        scores = calculate_market_score(
            stock
        )

        item = {
            "code":
                stock.get("code"),

            "name":
                stock.get("name"),

            "market":
                stock.get("market"),

            "previous_close":
                stock.get("previous_close"),

            "market_cap":
                stock.get("market_cap"),

            "trading_value":
                stock.get("trading_value"),

            "return_1d":
                stock.get("return_1d"),

            "return_5d":
                stock.get("return_5d"),

            "return_20d":
                stock.get("return_20d"),

            "volume_ratio_5d":
                stock.get("volume_ratio_5d"),

            "volume_ratio_20d":
                stock.get("volume_ratio_20d"),

            "distance_from_20d_high":
                stock.get(
                    "distance_from_20d_high"
                ),

            "volatility_20d":
                stock.get("volatility_20d"),

            **scores,

            "ranking_type":
                "MARKET_TECHNICAL_CANDIDATE",

            "prediction_eligible":
                False,
        }

        ranked.append(item)

    # IMPORTANT:
    # Tie-break logic is shared with the
    # historical backtest through market_score.py.
    ranked.sort(
        key=ranking_sort_key,
        reverse=True,
    )

    for index, stock in enumerate(
        ranked,
        start=1,
    ):
        stock["rank"] = index

    top = ranked[:TOP_N]

    feature_date = payload.get(
        "feature_date"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR
        / f"market_candidates_{feature_date}.json"
    )

    result = {
        "schema":
            "v511-market-ranking-v1",

        "feature_date":
            feature_date,

        "score_version":
            SCORE_VERSION,

        "ranking_type":
            "MARKET_TECHNICAL_CANDIDATE",

        "formal_prediction":
            False,

        "note":
            (
                "Price/Flow/Liquidity/Risk "
                "screen only. Catalyst, Theme, "
                "TDnet and live execution data "
                "are not included."
            ),

        "universe_count":
            len(stocks),

        "top_n":
            TOP_N,

        "candidates":
            top,
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
    log(
        "Universe stocks:",
        len(stocks)
    )

    log(
        "Ranking stocks:",
        len(ranked)
    )

    log("")
    log("==============================")
    log("TOP 30")
    log("==============================")

    for stock in top:

        log(
            f'{stock["rank"]:>2} '
            f'{stock["code"]} '
            f'{stock["name"]} '
            f'SCORE={stock["technical_score"]:.1f} '
            f'P={stock["price_score"]:.1f} '
            f'F={stock["flow_score"]:.1f} '
            f'L={stock["liquidity_score"]:.1f} '
            f'R={stock["risk_quality_score"]:.1f} '
            f'S={stock["size_score"]:.1f}'
        )

    log("")
    log("==============================")
    log(
        "MARKET CANDIDATE RANKING: PASS"
    )
    log("==============================")

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
