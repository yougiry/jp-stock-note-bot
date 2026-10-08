import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

URL = "https://note.com/api/v1/text_notes"

cookie = os.environ.get("NOTE_COOKIE", "")
cookie = cookie.strip().replace("\r", "").replace("\n", "")

if not cookie:
    raise RuntimeError("NOTE_COOKIE is empty")

now = datetime.now(ZoneInfo("Asia/Tokyo"))
title = f"API TEST - DELETE ME - {now:%Y-%m-%d %H:%M:%S}"

headers = {
    "Cookie": cookie,
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://editor.note.com",
    "Referer": "https://editor.note.com/",
}

payload = {
    "body": "",
    "body_length": 0,
    "name": title,
    "index": False,
    "is_lead_form": False
}

response = requests.post(
    URL,
    headers=headers,
    json=payload,
    timeout=30
)

print("HTTP STATUS:", response.status_code)

if response.status_code not in (200, 201):
    print("DRAFT CREATION: FAILED")

    # Cookieなどのヘッダーは絶対表示しない。
    # 422原因調査用にレスポンス本文だけ最大1000文字表示。
    safe_body = response.text[:1000]
    print("RESPONSE:", safe_body)

    raise SystemExit(1)

result = response.json()
data = result.get("data", {})

note_id = data.get("id")
note_key = data.get("key")

print("DRAFT CREATION: PASS")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)
print("TITLE:", title)

if not note_id:
    raise RuntimeError("Draft created but note_id was not returned")
