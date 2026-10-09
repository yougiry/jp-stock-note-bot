import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")

UNIVERSE_DIR = Path("data/universe")


# --------------------------------------------------
# LIVE Prediction policy
# --------------------------------------------------
#
# v5.11 no longer requires a dedicated real-time
# market-data API.
#
# Historical / delayed datasets may remain in the
# repository, but they must not automatically become
# scoring-eligible LIVE Prediction sources.
#
# J-Quants:
#   retained for historical / backtest use
#   NOT scoring eligible for LIVE Prediction
#
# Web / IR / TDnet / news discovery:
#   will be connected separately.
#
# Missing data:
#   represented as NA / unavailable
#   must never be guessed.
# --------------------------------------------------


def _latest_universe_file():
    files = sorted(
        UNIVERSE_DIR.glob(
            "v511_universe_????-??-??.json"
        )
    )

    return files[-1] if files else None


def _iso(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _build_source(
    *,
    source_id,
    source_type,
    source_tier,
    purpose,
    retrieval_timestamp,
    prediction_cutoff,
    publication_timestamp=None,
    scoring_eligible=False,
    factor_owner=None,
    snapshot_quality=None,
    prediction_role="REFERENCE",
    exclusion_reason=None,
):
    """
    Build one Source Audit Ledger entry.

    scoring_eligible must be explicitly supplied.
    A source never becomes scoring eligible merely
    because data exists.
    """

    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_tier": source_tier,
        "purpose": purpose,
        "publication_timestamp": (
            publication_timestamp
        ),
        "retrieval_timestamp": (
            retrieval_timestamp
        ),
        "prediction_cutoff": (
            prediction_cutoff
        ),
        "scoring_eligible": bool(
            scoring_eligible
        ),
        "factor_owner": factor_owner,
        "snapshot_quality": (
            snapshot_quality
        ),
        "prediction_role": (
            prediction_role
        ),
        "exclusion_reason": (
            exclusion_reason
        ),
    }


def collect_market_data(
    target_date,
    execution_time,
    prediction_cutoff=None,
):
    """
    Collect the base dataset for v5.11.

    This function currently loads the latest local
    universe/feature snapshot.

    IMPORTANT:

    The existence of historical/delayed market data
    does NOT make that data eligible for LIVE scoring.

    Web discovery, TDnet, IR, news and other
    cutoff-safe sources will be connected in later
    collection stages.
    """

    if prediction_cutoff is None:
        prediction_cutoff = execution_time

    execution_time_iso = _iso(
        execution_time
    )

    prediction_cutoff_iso = _iso(
        prediction_cutoff
    )

    print(
        "Target date:",
        target_date,
    )

    print(
        "Execution time:",
        execution_time_iso,
    )

    print(
        "Prediction cutoff:",
        prediction_cutoff_iso,
    )

    # --------------------------------------------------
    # Universe snapshot
    # --------------------------------------------------

    source = _latest_universe_file()

    if source is None:
        print(
            "UNIVERSE FEATURE FILE: NOT FOUND"
        )
        return None

    try:
        payload = json.loads(
            source.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(
            "UNIVERSE FEATURE FILE: INVALID"
        )
        print(exc)
        return None

    stocks = payload.get(
        "stocks",
        [],
    )

    try:
        coverage = float(
            payload.get(
                "coverage",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        coverage = 0.0

    feature_date = payload.get(
        "feature_date"
    )

    if not stocks:
        print(
            "UNIVERSE FEATURES EMPTY"
        )
        return None

    retrieval_time = (
        datetime.now(JST).isoformat()
    )

    # --------------------------------------------------
    # Source Audit Ledger
    # --------------------------------------------------

    sources = []

    # Universe membership is useful for determining
    # what securities exist, but it is not itself a
    # scoring factor.

    sources.append(
        _build_source(
            source_id=(
                "JPX_LISTED_COMPANIES"
            ),
            source_type="primary",
            source_tier="JPX",
            purpose="universe",
            publication_timestamp=None,
            retrieval_timestamp=(
                retrieval_time
            ),
            prediction_cutoff=(
                prediction_cutoff_iso
            ),
            scoring_eligible=False,
            factor_owner="Universe",
            snapshot_quality=(
                "PRIMARY_SOURCE"
            ),
            prediction_role=(
                "UNIVERSE_REFERENCE"
            ),
            exclusion_reason=(
                "Universe membership is not "
                "a scoring factor"
            ),
        )
    )

    # --------------------------------------------------
    # Historical / delayed J-Quants features
    # --------------------------------------------------
    #
    # Keep the data in the dataset for traceability,
    # research and future backtesting.
    #
    # It MUST NOT participate in LIVE Prediction
    # scoring.
    # --------------------------------------------------

    if feature_date:

        sources.append(
            _build_source(
                source_id=(
                    f"JQUANTS_DAILY_"
                    f"{feature_date}"
                ),
                source_type="primary",
                source_tier="J-Quants",
                purpose=(
                    "historical_price_volume_"
                    "reference"
                ),
                publication_timestamp=(
                    feature_date
                ),
                retrieval_timestamp=(
                    retrieval_time
                ),
                prediction_cutoff=(
                    prediction_cutoff_iso
                ),
                scoring_eligible=False,
                factor_owner=(
                    "HistoricalReference"
                ),
                snapshot_quality=(
                    "DELAYED_DAILY_CLOSE"
                ),
                prediction_role=(
                    "HISTORICAL_REFERENCE"
                ),
                exclusion_reason=(
                    "J-Quants Free data is "
                    "excluded from LIVE "
                    "Prediction scoring"
                ),
            )
        )

    # --------------------------------------------------
    # Collection status
    # --------------------------------------------------

    live_scoring_sources = [
        item
        for item in sources
        if item.get(
            "scoring_eligible"
        )
    ]

    print(
        "BASE DATA COLLECTION: PASS"
    )

    print(
        "FEATURE DATE:",
        feature_date or "NA",
    )

    print(
        "UNIVERSE:",
        len(stocks),
    )

    print(
        "DECLARED COVERAGE:",
        f"{coverage * 100:.2f}%",
    )

    print(
        "LIVE SCORING SOURCES:",
        len(live_scoring_sources),
    )

    if not live_scoring_sources:
        print(
            "LIVE MARKET FACTORS: NA"
        )

    # --------------------------------------------------
    # Return
    # --------------------------------------------------

    return {
        "target_date": target_date,

        "execution_time": (
            execution_time_iso
        ),

        "prediction_cutoff": (
            prediction_cutoff_iso
        ),

        "feature_date": (
            feature_date
        ),

        "stocks": stocks,

        "sources": sources,

        # Preserve the original declared coverage,
        # but do not represent it as verified LIVE
        # market-data coverage.
        "coverage": coverage,

        "coverage_status": (
            "DECLARED_UNIVERSE_COVERAGE"
        ),

        "live_market_coverage": None,

        "live_market_data_status": (
            "NA"
        ),

        "live_scoring_source_count": (
            len(
                live_scoring_sources
            )
        ),

        "collection_mode": (
            "BASE_UNIVERSE_WITH_"
            "DELAYED_REFERENCE"
        ),
    }
