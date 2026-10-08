import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


JST = ZoneInfo("Asia/Tokyo")

API_KEY = os.environ.get(
    "JQUANTS_API_KEY",
    ""
).strip()

BASE_URL = "https://api.jquants.com/v2"


def fail(message):
    print("")
    print("==============================")
    print("J-QUANTS PRICE TEST: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


if not API_KEY:
    fail("JQUANTS_API_KEY is not configured")


HEADERS = {
    "x-api-key": API_KEY
}


def request_daily_quotes(date_string):

    url = f"{BASE_URL}/equities/bars/daily"

    params = {
        "date": date_string
    }

    print("")
    print("REQUEST DATE:", date_string)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=60,
        )

    except requests.RequestException as e:
        fail(
            "Connection error: "
            + repr(e)
        )

    print(
        "HTTP STATUS:",
        response.status_code
    )

    if response.status_code != 200:

        print(
            "RESPONSE:",
            response.text[:1000]
        )

        return None

    try:
        return response.json()

    except ValueError:
        fail(
            "Response is not JSON"
        )


# ------------------------------------------------
# Look backwards until a trading day is found.
#
# We do NOT assume Monday-Friday is sufficient,
# because JPX holidays exist.
# ------------------------------------------------

today = datetime.now(JST).date()

found = None
found_date = None


for days_back in range(1, 11):

    candidate_date = (
        today - timedelta(days=days_back)
    )

    date_string = candidate_date.strftime(
        "%Y-%m-%d"
    )

    data = request_daily_quotes(
        date_string
    )

    if data is None:
        continue

    rows = data.get("data", [])

    print(
        "ROWS:",
        len(rows)
    )

    if rows:

        found = rows
        found_date = date_string

        break


if not found:

    fail(
        "No trading-day price data "
        "found in previous 10 days"
    )


print("")
print("==============================")
print("J-QUANTS DAILY PRICE: PASS")
print("==============================")

print(
    "TRADING DATE:",
    found_date
)

print(
    "ROWS:",
    len(found)
)


# ------------------------------------------------
# Inspect schema
# ------------------------------------------------

first = found[0]

print("")
print("FIELDS:")

for key in first.keys():
    print(
        " -",
        key
    )


print("")
print("FIRST 3 RECORDS:")

for row in found[:3]:

    safe = {}

    for key in [
        "Code",
        "Date",
        "O",
        "H",
        "L",
        "C",
        "Vo",
        "Va",
        "AdjFactor",
        "AdjC",
    ]:

        if key in row:
            safe[key] = row[key]

    print(safe)
