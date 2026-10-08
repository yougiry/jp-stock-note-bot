from datetime import datetime
from zoneinfo import ZoneInfo

from collect_universe import collect_jpx_universe


JST = ZoneInfo("Asia/Tokyo")


def collect_market_data(
    target_date,
    execution_time,
):

    print(
        "Target date:",
        target_date
    )

    print(
        "Prediction cutoff:",
        execution_time.isoformat()
    )

    # ==========================================
    # JPX Universe
    # ==========================================

    retrieval_time = datetime.now(JST)

    try:
        stocks = collect_jpx_universe()

    except Exception as e:

        print(
            "JPX UNIVERSE FAILED:",
            repr(e)
        )

        return None

    if not stocks:

        print(
            "JPX UNIVERSE EMPTY"
        )

        return None

    # ==========================================
    # Source Audit
    # ==========================================

    sources = [{
        "source_id":
            "JPX_LISTED_COMPANIES",

        "source_type":
            "primary",

        "source_tier":
            "JPX",

        "purpose":
            "universe",

        "url":
            (
                "https://www.jpx.co.jp/"
                "markets/statistics-equities/"
                "misc/01.html"
            ),

        "publication_timestamp":
            None,

        "retrieval_timestamp":
            retrieval_time.isoformat(),

        "prediction_cutoff":
            execution_time.isoformat(),

        "scoring_eligible":
            False,

        "factor_owner":
            "Universe",

        "snapshot_quality":
            "PRIMARY_SOURCE",
    }]

    dataset = {
        "target_date":
            target_date,

        "execution_time":
            execution_time.isoformat(),

        "stocks":
            stocks,

        "sources":
            sources,

        # これはまだ価格データCoverageではない。
        "coverage":
            0.0,
    }

    print(
        "MARKET DATA COLLECTION: PASS"
    )

    print(
        "UNIVERSE:",
        len(stocks)
    )

    return dataset
