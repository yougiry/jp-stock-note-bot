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
# Current historical lane ends here.
END_DATE = date(2026, 7, 16)

TARGET_TRADING_DAYS = 80

# Target number of newly SAVED trading days
# in one GitHub Actions run.
MAX_SUCCESSFUL_DAYS_PER_RUN = 5

# Safety gate:
# Holidays / invalid dates do not consume the
# successful-day quota, but API requests still
# need a hard upper bound.
MAX_API_REQUESTS_PER_RUN = 10

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
        RAW_DIR
        / f"{target_date.isoformat()}.json"
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

    log(
        "Target trading days:",
        TARGET_TRADING_DAYS
    )

    log(
        "Max successful days/run:",
        MAX_SUCCESSFUL_DAYS_PER_RUN
    )

    log(
        "Max API requests/run:",
        MAX_API_REQUESTS_PER_RUN
    )

    if len(existing) >= TARGET_TRADING_DAYS:

        log(
            "TARGET ALREADY COMPLETE"
        )

        log(
            "HISTORY STATUS: COMPLETE"
        )

        sys.exit(0)

    current = END_DATE

    requests_used = 0
    successful_days = 0
    skipped_existing = 0
    skipped_weekends = 0
    no_data_days = 0
    invalid_dates = 0

    while (
        successful_days
        < MAX_SUCCESSFUL_DAYS_PER_RUN
        and requests_used
        < MAX_API_REQUESTS_PER_RUN
    ):

        # Re-check target during the run.
        current_existing_count = (
            len(existing)
            + successful_days
        )

        if (
            current_existing_count
            >= TARGET_TRADING_DAYS
        ):

            break

        date_string = (
            current.isoformat()
        )

        output = (
            RAW_DIR
            / f"{date_string}.json"
        )

        # Already downloaded.
        # No API request is consumed.
        if output.exists():

            skipped_existing += 1

            current -= timedelta(
                days=1
            )

            continue

        # Never request Saturdays/Sundays.
        # No API request is consumed.
        if current.weekday() >= 5:

            skipped_weekends += 1

            current -= timedelta(
                days=1
            )

            continue

        status, rows = fetch_day(
            current
        )

        requests_used += 1

        # Stop immediately.
        # Do not keep hammering the API.
        if status == "RATE_LIMIT":

            break

        if status == "INVALID_DATE":

            invalid_dates += 1

            current -= timedelta(
                days=1
            )

            time.sleep(2)

            continue

        # Exchange holiday or otherwise
        # no daily bars returned.
        if not rows:

            no_data_days += 1

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

        successful_days += 1

        current -= timedelta(
            days=1
        )

        # Conservative spacing.
        time.sleep(3)

    final_existing = (
        existing_trading_days()
    )

    log("")
    log("==============================")
    log("PRICE HISTORY RUN COMPLETE")
    log("==============================")

    log(
        "API requests this run:",
        requests_used
    )

    log(
        "Successful trading days:",
        successful_days
    )

    log(
        "Skipped existing:",
        skipped_existing
    )

    log(
        "Skipped weekends:",
        skipped_weekends
    )

    log(
        "No-data weekdays:",
        no_data_days
    )

    log(
        "Invalid dates:",
        invalid_dates
    )

    log(
        "Stored trading days:",
        len(final_existing)
    )

    log(
        "Target trading days:",
        TARGET_TRADING_DAYS
    )

    if (
        len(final_existing)
        >= TARGET_TRADING_DAYS
    ):

        log(
            "HISTORY STATUS: COMPLETE"
        )

    else:

        log(
            "HISTORY STATUS: PARTIAL"
        )


if __name__ == "__main__":
    main()
