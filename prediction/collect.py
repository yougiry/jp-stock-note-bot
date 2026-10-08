import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
UNIVERSE_DIR = Path("data/universe")


def _latest_universe_file():
    files = sorted(UNIVERSE_DIR.glob("v511_universe_????-??-??.json"))
    return files[-1] if files else None


def collect_market_data(target_date, execution_time):
    print("Target date:", target_date)
    print("Prediction cutoff:", execution_time.isoformat())

    source = _latest_universe_file()
    if source is None:
        print("UNIVERSE FEATURE FILE: NOT FOUND")
        return None

    payload = json.loads(source.read_text(encoding="utf-8"))
    stocks = payload.get("stocks", [])
    coverage = float(payload.get("coverage", 0) or 0)
    feature_date = payload.get("feature_date")

    if not stocks:
        print("UNIVERSE FEATURES EMPTY")
        return None

    retrieval_time = datetime.now(JST).isoformat()
    sources = [
        {
            "source_id": "JPX_LISTED_COMPANIES",
            "source_type": "primary",
            "source_tier": "JPX",
            "purpose": "universe",
            "publication_timestamp": None,
            "retrieval_timestamp": retrieval_time,
            "prediction_cutoff": execution_time.isoformat(),
            "scoring_eligible": False,
            "factor_owner": "Universe",
            "snapshot_quality": "PRIMARY_SOURCE",
        },
        {
            "source_id": f"JQUANTS_DAILY_{feature_date}",
            "source_type": "primary",
            "source_tier": "J-Quants",
            "purpose": "price_volume_features",
            "publication_timestamp": feature_date,
            "retrieval_timestamp": retrieval_time,
            "prediction_cutoff": execution_time.isoformat(),
            "scoring_eligible": True,
            "factor_owner": "Price/Flow/Liquidity/Risk/Size",
            "snapshot_quality": "DAILY_CLOSE",
        },
    ]

    print("MARKET DATA COLLECTION: PASS")
    print("FEATURE DATE:", feature_date)
    print("UNIVERSE:", len(stocks))
    print("COVERAGE:", f"{coverage * 100:.2f}%")

    return {
        "target_date": target_date,
        "execution_time": execution_time.isoformat(),
        "feature_date": feature_date,
        "stocks": stocks,
        "sources": sources,
        "coverage": coverage,
    }
