import json
import os
import sys
from datetime import date
from pathlib import Path

import requests


API_KEY = os.environ.get(
    "JQUANTS_API_KEY",
    ""
).strip()

BASE_URL = "https://api.jquants.com/v2"

TEST_DATE = date(2026, 7, 16)

OUTPUT_DIR = Path(
    "data/market/jquants"
)


def log(*args):
    print(*args, flush=True)


def fail(message, code=1):
    log("")
    log("==============================")
    log("J-QUANTS HISTORY: FAILED")
    log(message)
    log("==============================")
    sys.exit(code)


def main():

    if not API_KEY:
        fail(
            "JQUANTS_API_KEY is missing"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = TEST_DATE.isoformat()

    url = (
        f"{BASE_URL}/equities/bars/daily"
    )

    params = {
        "date": target
    }

    headers = {
        "x-api-key": API_KEY
    }

    log("")
    log("==============================")
    log("J-QUANTS HISTORY TEST")
    log("==============================")
    log("DATE:", target)
    log("REQUEST: START")

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=(10, 30),
        )

    except requests.Timeout:

        fail(
            "API request timed out",
            2,
        )

    except requests.RequestException as e:

        fail(
            "Connection error: "
            + repr(e),
            3,
        )

    log(
        "HTTP STATUS:",
        response.status_code
    )

    # ------------------------------
    # Rate limit
    # ------------------------------

    if response.status_code == 429:

        log(
            "RESPONSE:",
            response.text[:500]
        )

        fail(
            "RATE LIMIT - no retry",
            4,
        )

    # ------------------------------
    # Subscription/date range
    # ------------------------------

    if response.status_code == 400:

        log(
            "RESPONSE:",
            response.text[:500]
        )

        fail(
            "Subscription/date-range error",
            5,
        )

    # ------------------------------
    # Authentication
    # ------------------------------

    if response.status_code in (
        401,
        403,
    ):

        fail(
            "Authentication/"
            "permission error",
            6,
        )

    if response.status_code != 200:

        log(
            "RESPONSE:",
            response.text[:500]
        )

        fail(
            f"Unexpected HTTP "
            f"{response.status_code}",
            7,
        )

    try:

        payload = response.json()

    except ValueError:

        fail(
            "Response is not JSON",
            8,
        )

    rows = payload.get(
        "data",
        []
    )

    log(
        "ROWS:",
        len(rows)
    )

    if not rows:

        fail(
            "HTTP 200 but no rows returned",
            9,
        )

    # ------------------------------
    # Schema inspection
    # ------------------------------

    log("")
    log("FIELDS:")

    for field in rows[0].keys():
        log(
            " -",
            field
        )

    # ------------------------------
    # Save
    # ------------------------------

    output_file = (
        OUTPUT_DIR /
        f"{target}.json"
    )

    result = {
        "date":
            target,

        "source":
            "J-Quants",

        "rows":
            rows,
    }

    output_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log("")
    log(
        "SAVED:",
        output_file
    )

    log("")
    log("==============================")
    log("J-QUANTS HISTORY: SUCCESS")
    log("==============================")

    log(
        "DATE:",
        target
    )

    log(
        "ROWS:",
        len(rows)
    )


if __name__ == "__main__":
    main()
