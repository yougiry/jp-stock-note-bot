import os
import sys
import requests


API_KEY = os.environ.get("JQUANTS_API_KEY")

BASE_URL = "https://api.jquants.com/v2"


def fail(message):
    print("")
    print("==============================")
    print("J-QUANTS TEST: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


if not API_KEY:
    fail("JQUANTS_API_KEY is not configured")


headers = {
    "x-api-key": API_KEY,
}


print("")
print("==============================")
print("J-QUANTS API CONNECTION TEST")
print("==============================")
print("API key: configured")


url = f"{BASE_URL}/equities/master"


try:
    response = requests.get(
        url,
        headers=headers,
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

    # Secret自体は絶対に表示しない
    safe_body = response.text[:500]

    print(
        "RESPONSE:",
        safe_body
    )

    fail(
        "J-Quants API returned "
        f"HTTP {response.status_code}"
    )


try:
    data = response.json()

except ValueError:
    fail(
        "Response is not valid JSON"
    )


print("")
print("==============================")
print("J-QUANTS CONNECTION: PASS")
print("==============================")

print(
    "Response keys:",
    list(data.keys())
)
