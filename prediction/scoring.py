from market_score import (
    SCORE_VERSION,
    calculate_market_score,
    ranking_sort_key,
)


MAX_CANDIDATES = 15


def run_scoring(
    market_data,
    audit,
    prediction_cutoff,
):
    """
    v5.11 Production scoring.

    Uses the currently implemented market_score engine.
    No probability calibration is performed here.
    Scores are ranking scores, not probabilities.
    """

    stocks = market_data.get(
        "stocks",
        []
    )

    if not stocks:
        return None

    ranked = []

    for stock in stocks:

        if not isinstance(stock, dict):
            continue

        code = str(
            stock.get("code", "")
        ).strip()

        if not code:
            continue

        try:
            scores = calculate_market_score(
                stock
            )
        except Exception as exc:
            print(
                "SCORING SKIP:",
                code,
                str(exc)
            )
            continue

        if not scores:
            continue

        item = {
            **stock,
            **scores,
        }

        ranked.append(item)

    if not ranked:
        return None

    # Same ranking rule as the existing
    # production market-score implementation.
    ranked.sort(
        key=ranking_sort_key,
        reverse=True,
    )

    candidates = []

    for rank, stock in enumerate(
        ranked[:MAX_CANDIDATES],
        start=1,
    ):

        technical_score = stock.get(
            "technical_score",
            0
        )

        # Simple production labels.
        # These are rule-based labels,
        # NOT calibrated probabilities.
        if technical_score >= 80:
            decision = "買い候補"
        elif technical_score >= 65:
            decision = "監視"
        else:
            decision = "除外"

        previous_close = stock.get(
            "previous_close",
            0
        ) or 0

        try:
            previous_close = float(
                previous_close
            )
        except (TypeError, ValueError):
            previous_close = 0

        required_capital = int(
            previous_close * 100
        )

        reason = (
            f"Technical Score "
            f"{technical_score}/100。"
            f"Price={stock.get('price_score', 0)}, "
            f"Flow={stock.get('flow_score', 0)}, "
            f"Liquidity={stock.get('liquidity_score', 0)}, "
            f"Risk={stock.get('risk_score', 0)}, "
            f"Size={stock.get('size_score', 0)}。"
        )

        candidates.append({
            "rank":
                rank,

            "code":
                stock.get("code"),

            "name":
                stock.get("name", ""),

            "decision":
                decision,

            "previous_close":
                previous_close,

            "required_capital":
                required_capital,

            # Current score is a ranking score.
            # Do not represent it as probability.
            "surge_score":
                technical_score,

            "limit_up_score":
                "未校正",

            "entry_score":
                technical_score,

            "risk":
                ("低" if stock.get("risk_quality_score", 0) >= 16 else
                 "中" if stock.get("risk_quality_score", 0) >= 10 else "高"),

            "reason":
                reason,

            "technical_score":
                technical_score,

            "price_score":
                stock.get(
                    "price_score"
                ),

            "flow_score":
                stock.get(
                    "flow_score"
                ),

            "liquidity_score":
                stock.get(
                    "liquidity_score"
                ),

            "risk_score":
                stock.get(
                    "risk_quality_score"
                ),

            "size_score":
                stock.get(
                    "size_score"
                ),
        })

    if not candidates:
        return None

    print(
        "SCORING: PASS"
    )

    print(
        "SCORE VERSION:",
        SCORE_VERSION
    )

    print(
        "RANKED STOCKS:",
        len(ranked)
    )

    print(
        "CANDIDATES:",
        len(candidates)
    )

    for candidate in candidates[:5]:
        print(
            candidate["rank"],
            candidate["code"],
            candidate["name"],
            candidate["technical_score"],
            candidate["decision"],
        )

    return {
        "status":
            "VALID",

        "score_version":
            SCORE_VERSION,

        "prediction_cutoff":
            prediction_cutoff.isoformat(),

        "ranking_type":
            "MARKET_TECHNICAL_CANDIDATE",

        "formal_prediction":
            False,

        "coverage":
            float(market_data.get("coverage", 0) or 0),

        "candidate_count":
            len(candidates),

        "candidates":
            candidates,
    }
