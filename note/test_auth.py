import os
import requests

URL = "https://note.com/api/v3/notice_counts"

cookie = os.environ.get("NOTE_COOKIE")

if not cookie:
    raise RuntimeError("NOTE_COOKIE is not set")

headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

print("HTTP STATUS:", response.status_code)

if response.status_code != 200:
    print("Authentication failed")
    raise SystemExit(1)

print("NOTE AUTHENTICATION: PASS")
