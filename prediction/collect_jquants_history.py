import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests


API_KEY = os.environ.get(
    "JQUANTS_API_KEY",
    ""
).strip()

BASE_URL = "https://api.jquants.com/v2"

START_DATE = date(2026, 6, 1)
END_DATE = date(2026, 7, 16)

OUTPUT_DIR = Path(
    "data/market/jquants"
)

HEADERS = {
    "x-api-key": API_KEY
}


def fail(message):
    print("")
    print("==============================")
    print("J-QUANTS HISTORY: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


def fetch_date(target_date):

    url = (
        f"{BASE_URL}/equities/bars/daily"
    )

    params = {
        "date": target_date.isoformat()
    }

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=60,
    )

    print(
        target_date,
        "HTTP",
        response.status_code,
    )

    # -----------------------------
    # Subscription error
    # -----------------------------

    if response.status_code == 400:
        print(response.text[:500])

        fail(
            "Subscription/date-range error"
        )

    # -----------------------------
    # Authentication
    # -----------------------------

    if response.status_code in (
        401,
        403,
    ):
        fail(
            "Authentication/permission error"
        )

    # -----------------------------
    # Rate limit
    # -----------------------------

    if response.status_code == 429:

        print(
            "RATE LIMIT - wait 60 seconds"
        )

        time.sleep(60)

        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=60,
        )

        print(
            target_date,
            "RETRY HTTP",
            response.status_code,
        )

        if response.status_code == 429:
            fail(
                "Rate limit after retry"
            )

    if response.status_code != 200:
        fail(
            f"Unexpected HTTP "
            f"{response.status_code}"
        )

    data = response.json()

    return data.get(
        "data",
        []
    )


def main():

    if not API_KEY:
        fail(
            "JQUANTS_API_KEY is missing"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    current = START_DATE

    trading_days = 0
    total_rows = 0

    while current <= END_DATE:

        # Weekendは問い合わせない
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        output_file = (
            OUTPUT_DIR /
            f"{current.isoformat()}.json"
        )

        # -----------------------------
        # Resume support
        # -----------------------------

        if output_file.exists():

            print(
                current,
                "SKIP - already stored"
            )

            current += timedelta(days=1)
            continue

        rows = fetch_date(
            current
        )

        # 祝日等は0件
        if not rows:

            print(
                current,
                "NO DATA"
            )

            current += timedelta(days=1)

            time.sleep(1)

            continue

        payload = {
            "date":
                current.isoformat(),

            "source":
                "J-Quants",

            "rows":
                rows,
        }

        output_file.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        trading_days += 1
        total_rows += len(rows)

        print(
            "SAVED:",
            output_file,
            "ROWS:",
            len(rows),
        )

        # Freeプランを乱暴に叩かない
        time.sleep(2)

        current += timedelta(days=1)

    print("")
    print("==============================")
    print("J-QUANTS HISTORY: SUCCESS")
    print("==============================")

    print(
        "Trading days downloaded:",
        trading_days,
    )

    print(
        "Total rows:",
        total_rows,
    )


if __name__ == "__main__":
    main()
