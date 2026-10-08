import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://note.com/api"

cookie = os.environ.get("NOTE_COOKIE", "")
cookie = cookie.strip().replace("\r", "").replace("\n", "")

if not cookie:
    raise RuntimeError("NOTE_COOKIE is empty")

session = requests.Session()

session.headers.update({
    "Cookie": cookie,
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://editor.note.com",
    "Referer": "https://editor.note.com/",
})

now = datetime.now(ZoneInfo("Asia/Tokyo"))

title = f"API TEST - DELETE ME - {now:%Y-%m-%d %H:%M:%S}"

payload = {
    "body": "",
    "body_length": 0,
    "name": title,
    "index": False,
    "is_lead_form": False,
}

url = f"{BASE_URL}/v1/text_notes"

response = session.post(
    url,
    json=payload,
    timeout=30
)

print("HTTP STATUS:", response.status_code)

if response.status_code not in (200, 201):
    print("DRAFT CREATION: FAILED")
    # 認証情報を含む可能性があるため本文は表示しない
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
