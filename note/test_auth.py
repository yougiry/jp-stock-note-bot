import os
import requests

URL = "https://note.com/api/v3/notice_counts"

cookie = os.environ.get("NOTE_COOKIE", "")

# GitHub Secretへのコピー時に混入した
# 前後の空白・改行を除去
cookie = cookie.strip()

# Cookieヘッダーには改行を含められない
cookie = cookie.replace("\r", "").replace("\n", "")

if not cookie:
    raise RuntimeError("NOTE_COOKIE is empty")

print("NOTE_COOKIE loaded")
print("Cookie length:", len(cookie))
# Cookieそのものは絶対にprintしない

headers = {
    "Cookie": cookie,
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://note.com/",
}

response = requests.get(
    URL,
    headers=headers,
    timeout=20
)

print("HTTP STATUS:", response.status_code)

if response.status_code != 200:
    print("NOTE AUTHENTICATION: FAILED")
    raise SystemExit(1)

print("NOTE AUTHENTICATION: PASS")
