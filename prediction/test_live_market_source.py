"""Test a candidate LIVE market-data source.

This script does NOT feed data into Prediction Engine v5.11.
It only tests availability, freshness and schema compatibility.
"""

import csv
import io
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from market_data_adapter import (
    MarketDataError,
    normalize_bar,
)


JST = ZoneInfo("Asia/Tokyo")

TEST_CODES = [
    "7203",  # Toyota
    "6758",  # Sony Group
    "9984",  # SoftBank Group
    "8306",  # Mitsubishi UFJ
    "9432",  # NTT
]

BASE_URL = "https://stooq.com/q/d/l/"

TIMEOUT = (10, 30)


def log(*args):
    print(*args, flush=True)


def fetch(code):
    symbol = f"{code}.jp"

    response = requests.get(
        BASE_URL,
        params={
            "s": symbol,
            "d1": "20260901",
            "i": "d",
        },
        timeout=TIMEOUT,
        headers={
            "User-Agent":
                "jp-stock-note-bot/market-source-test"
        },
    )

    log(
        "REQUEST:",
        symbol,
        "HTTP:",
        response.status_code,
    )

    if response.status_code != 200:
        return None

    text = response.text.strip()

    if not text:
        return None

    reader = csv.DictReader(
        io.StringIO(text)
    )

    rows = list(reader)

    if not rows:
        return None

    latest = rows[-1]

    if not latest.get("Date"):
        return None

    retrieved_at = datetime.now(
        JST
    ).isoformat()

    raw = {
        "code": code,
        "date": latest.get("Date"),
        "open": latest.get("Open"),
        "high": latest.get("High"),
        "low": latest.get("Low"),
        "close": latest.get("Close"),
        "volume": latest.get("Volume"),
        "turnover": None,
        "publication_at": None,
    }

    try:
        return normalize_bar(
            raw,
            source="STOOQ_TEST",
            retrieved_at=retrieved_at,
        )

    except MarketDataError as exc:
        log(
            "NORMALIZATION ERROR:",
            code,
            str(exc),
        )
        return None


def main():
    log("")
    log("==============================")
    log("LIVE MARKET SOURCE TEST")
    log("==============================")

    results = []

    for code in TEST_CODES:
        result = fetch(code)

        if result is None:
            log(
                "FAILED:",
                code,
            )
            continue

        results.append(result)

        log(
            "PASS:",
            result["code"],
            result["date"],
            result["close"],
            result["volume"],
        )

    log("")
    log("==============================")
    log("RESULT")
    log("==============================")

    log(
        "Requested:",
        len(TEST_CODES),
    )

    log(
        "Successful:",
        len(results),
    )

    if results:
        dates = sorted(
            {
                item["date"]
                for item in results
            }
        )

        log(
            "Returned dates:",
            dates,
        )

    # This is deliberately NOT a production
    # coverage decision.
    if not results:
        log(
            "SOURCE TEST: FAILED"
        )
        sys.exit(1)

    log(
        "SOURCE TEST: COMPLETED"
    )


if __name__ == "__main__":
    main()
