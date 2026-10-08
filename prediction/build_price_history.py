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

# Historical test period.
# J-Quants Free coverage confirmed through 2026-07-16.
END_DATE = date(2026, 7, 16)

TARGET_TRADING_DAYS = 60

# Limit requests per single GitHub Actions run.
MAX_REQUESTS_PER_RUN = 5

RAW_DIR = Path(
    "data/market/jquants"
)

HEADERS = {
    "x-api-key": API_KEY
}


def log(*args):
    print(*args, flush=True)


def fail(message, code=1):
    log("")
    log("==============================")
    log("PRICE HISTORY: FAILED")
    log(message)
    log("==============================")
    sys.exit(code)


def fetch_day(target_date):

    url = (
        f"{BASE_URL}/equities/bars/daily"
    )

    params = {
        "date": target_date.isoformat()
    }

    log(
        "REQUEST:",
        target_date.isoformat()
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=(10, 30),
        )

    except requests.RequestException as e:
        fail(
            "Connection error: "
            + repr(e)
        )

    log(
        "HTTP:",
        response.status_code
    )

    if response.status_code == 429:
        log(
            "RATE LIMIT reached."
        )
        return "RATE_LIMIT", None

    if response.status_code == 400:
        log(
            "RESPONSE:",
            response.text[:300]
        )
        return "INVALID_DATE", None

    if response.status_code in (
        401,
        403,
    ):
        fail(
            "Authentication/permission error"
        )

    if response.status_code != 200:
        fail(
            f"Unexpected HTTP "
            f"{response.status_code}"
        )

    payload = response.json()

    rows = payload.get(
        "data",
        []
    )

    return "OK", rows


def save_day(
    target_date,
    rows,
):

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        RAW_DIR /
        f"{target_date.isoformat()}.json"
    )

    payload = {
        "date":
            target_date.isoformat(),

        "source":
            "J-Quants",

        "rows":
            rows,
    }

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log(
        "SAVED:",
        output,
        "ROWS:",
        len(rows)
    )


def existing_trading_days():

    if not RAW_DIR.exists():
        return []

    files = sorted(
        RAW_DIR.glob(
            "????-??-??.json"
        )
    )

    valid = []

    for file in files:

        try:
            payload = json.loads(
                file.read_text(
                    encoding="utf-8"
                )
            )

            rows = payload.get(
                "rows",
                []
            )

            if rows:
                valid.append(
                    file.stem
                )

        except Exception:
            continue

    return valid


def main():

    if not API_KEY:
        fail(
            "JQUANTS_API_KEY missing"
        )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = existing_trading_days()

    log("")
    log("==============================")
    log("v5.11 PRICE HISTORY BUILDER")
    log("==============================")

    log(
        "Existing trading days:",
        len(existing)
    )

    if len(existing) >= TARGET_TRADING_DAYS:

        log(
            "TARGET ALREADY COMPLETE"
        )

        sys.exit(0)

    current = END_DATE

    requests_used = 0

    while requests_used < MAX_REQUESTS_PER_RUN:

        date_string = (
            current.isoformat()
        )

        output = (
            RAW_DIR /
            f"{date_string}.json"
        )

        # Already downloaded
        if output.exists():

            current -= timedelta(
                days=1
            )

            continue

        # Never request weekends
        if current.weekday() >= 5:

            current -= timedelta(
                days=1
            )

            continue

        status, rows = fetch_day(
            current
        )

        requests_used += 1

        if status == "RATE_LIMIT":
            break

        if status == "INVALID_DATE":

            current -= timedelta(
                days=1
            )

            continue

        # Holiday
        if not rows:

            log(
                "NO DATA:",
                date_string
            )

            current -= timedelta(
                days=1
            )

            time.sleep(2)

            continue

        save_day(
            current,
            rows,
        )

        current -= timedelta(
            days=1
        )

        # Conservative spacing
        time.sleep(3)

    existing = existing_trading_days()

    log("")
    log("==============================")
    log("PRICE HISTORY RUN COMPLETE")
    log("==============================")

    log(
        "Requests this run:",
        requests_used
    )

    log(
        "Stored trading days:",
        len(existing)
    )

    log(
        "Target trading days:",
        TARGET_TRADING_DAYS
    )

    if len(existing) >= TARGET_TRADING_DAYS:
        log(
            "HISTORY STATUS: COMPLETE"
        )
    else:
        log(
            "HISTORY STATUS: PARTIAL"
        )


if __name__ == "__main__":
    main()
