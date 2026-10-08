"""Bootstrap J-Quants daily-bar history for Prediction Engine v5.11.

This script is intended for initial setup/recovery.
Normal daily freshness updates are handled by sync_latest_market.py.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


JST = ZoneInfo("Asia/Tokyo")

API_KEY = os.environ.get(
    "JQUANTS_API_KEY",
    "",
).strip()

BASE_URL = (
    "https://api.jquants.com/v2/equities/bars/daily"
)

OUTPUT_DIR = Path(
    "data/market/jquants"
)

# Calendar days to inspect.
# This should provide enough trading days for
# 20-day factors plus a safety margin.
LOOKBACK_CALENDAR_DAYS = 45

REQUEST_TIMEOUT = (10, 45)
REQUEST_INTERVAL_SECONDS = 0.25


def log(*args):
    print(*args, flush=True)


def fail(message, code=1):
    log("")
    log("==============================")
    log("J-QUANTS BOOTSTRAP: FAILED")
    log(message)
    log("==============================")
    sys.exit(code)


def load_cached(path):
    if not path.exists():
        return None

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return None

    rows = payload.get("rows", [])

    if not rows:
        return None

    return payload


def fetch_day(day, headers):
    target = day.isoformat()

    response = requests.get(
        BASE_URL,
        headers=headers,
        params={"date": target},
        timeout=REQUEST_TIMEOUT,
    )

    log(
        "REQUEST:",
        target,
        "HTTP:",
        response.status_code,
    )

    if response.status_code == 429:
        fail(
            "J-Quants rate limit reached",
            4,
        )

    if response.status_code in (401, 403):
        fail(
            "J-Quants authentication/"
            "permission error",
            6,
        )

    # Depending on subscription/data availability,
    # unavailable dates may not return usable data.
    if response.status_code != 200:
         log(
            "RESPONSE:",
            response.text[:1000],
        )
        return None

    try:
        payload = response.json()
    except ValueError:
        log(
            "INVALID JSON:",
            target,
        )
        return None

    rows = payload.get("data", [])

    if not rows:
        log(
            "NO DATA:",
            target,
        )
        return None

    return {
        "date": target,
        "source": "J-Quants",
        "retrieved_at":
            datetime.now(JST).isoformat(),
        "rows": rows,
    }


def main():
    if not API_KEY:
        fail(
            "JQUANTS_API_KEY is missing"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    headers = {
        "x-api-key": API_KEY
    }

    today = datetime.now(JST).date()

    log("")
    log("==============================")
    log("J-QUANTS HISTORY BOOTSTRAP")
    log("==============================")

    log(
        "Execution:",
        datetime.now(JST).isoformat(),
    )

    log(
        "Calendar lookback:",
        LOOKBACK_CALENDAR_DAYS,
    )

    downloaded = 0
    cached = 0
    no_data = 0

    # Oldest -> newest makes the local history
    # deterministic and easier to inspect.
    days = [
        today - timedelta(days=offset)
        for offset in range(
            LOOKBACK_CALENDAR_DAYS,
            0,
            -1,
        )
    ]

    for day in days:
        # Saturday / Sunday
        if day.weekday() >= 5:
            continue

        output = (
            OUTPUT_DIR /
            f"{day.isoformat()}.json"
        )

        existing = load_cached(output)

        if existing is not None:
            cached += 1

            log(
                "CACHED:",
                day.isoformat(),
                "ROWS:",
                len(
                    existing.get(
                        "rows",
                        [],
                    )
                ),
            )

            continue

        result = fetch_day(
            day,
            headers,
        )

        if result is None:
            no_data += 1
            continue

        output.write_text(
            json.dumps(
                result,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        downloaded += 1

        log(
            "SAVED:",
            day.isoformat(),
            "ROWS:",
            len(result["rows"]),
        )

        time.sleep(
            REQUEST_INTERVAL_SECONDS
        )

    valid_files = []

    for path in sorted(
        OUTPUT_DIR.glob(
            "????-??-??.json"
        )
    ):
        if load_cached(path) is not None:
            valid_files.append(path)

    log("")
    log("==============================")
    log("BOOTSTRAP SUMMARY")
    log("==============================")

    log(
        "Downloaded:",
        downloaded,
    )

    log(
        "Already cached:",
        cached,
    )

    log(
        "No data:",
        no_data,
    )

    log(
        "Valid trading-day files:",
        len(valid_files),
    )

    if len(valid_files) < 20:
        fail(
            "Insufficient trading-day history. "
            f"Only {len(valid_files)} valid "
            "daily files are available.",
            10,
        )

    log("")
    log(
        "Oldest:",
        valid_files[0].stem,
    )

    log(
        "Newest:",
        valid_files[-1].stem,
    )

    log("")
    log("==============================")
    log("J-QUANTS BOOTSTRAP: PASS")
    log("==============================")
    

if __name__ == "__main__":
    main()
