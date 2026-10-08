"""Fetch the most recent available J-Quants daily bars and cache them.
This is the production freshness lane; historical backfill remains separate.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

JST = ZoneInfo("Asia/Tokyo")
API_KEY = os.environ.get("JQUANTS_API_KEY", "").strip()
BASE_URL = "https://api.jquants.com/v2/equities/bars/daily"
RAW_DIR = Path("data/market/jquants")
LOOKBACK_DAYS = 10


def fail(msg):
    print("LATEST MARKET SYNC: FAILED", msg)
    sys.exit(1)


def main():
    if not API_KEY:
        fail("JQUANTS_API_KEY missing")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(JST).date()
    headers = {"x-api-key": API_KEY}

    for days_back in range(1, LOOKBACK_DAYS + 1):
        day = today - timedelta(days=days_back)
        if day.weekday() >= 5:
            continue
        path = RAW_DIR / f"{day.isoformat()}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("rows"):
                print("LATEST MARKET ALREADY CACHED:", day)
                return

        response = requests.get(
            BASE_URL,
            headers=headers,
            params={"date": day.isoformat()},
            timeout=(10, 45),
        )
        print("REQUEST:", day, "HTTP:", response.status_code)
        if response.status_code == 429:
            fail("J-Quants rate limit")
        if response.status_code in (401, 403):
            fail("J-Quants authentication/permission error")
        if response.status_code != 200:
            continue

        rows = response.json().get("data", [])
        if not rows:
            continue

        path.write_text(
            json.dumps({"date": day.isoformat(), "source": "J-Quants", "rows": rows},
                       ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print("LATEST MARKET SYNC: PASS", day, "ROWS:", len(rows))
        return

    fail("No trading-day data found in lookback window")


if __name__ == "__main__":
    main()
