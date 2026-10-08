import json
import os
import re
import requests
from pathlib import Path

ARTICLE = Path("output/article.md")
META = Path("output/article_meta.json")
EYECATCH = Path("output/eyecatch.png")
PUBLISHED = Path("data/published")


def fail(message, response=None):
    print("PROCESS FAILED:", message)

    if response is not None:
        print("STATUS:", response.status_code)
        print(response.text[:1500])

    raise SystemExit(1)


body = ARTICLE.read_text(encoding="utf-8").strip()
meta = json.loads(META.read_text(encoding="utf-8"))

title = meta["title"]
hashtags = meta["hashtags"]
target_date = meta.get("target_date", "")

if not body:
    fail("Article is empty")

if not EYECATCH.exists():
    fail("Eyecatch is missing")

cookie = os.environ.get("NOTE_COOKIE", "").strip()

if not cookie:
    fail("NOTE_COOKIE is empty")

PUBLISHED.mkdir(parents=True, exist_ok=True)

marker_name = re.sub(
    r"[^0-9A-Za-z_-]",
    "_",
    target_date or "latest",
)

marker = PUBLISHED / f"{marker_name}.json"

if marker.exists():
    print("ALREADY PUBLISHED")
    raise SystemExit(0)


session = requests.Session()

session.headers.update({
    "Cookie": cookie,
    "User-Agent":
        "Mozilla/5.0 AppleWebKit/537.36 "
        "Chrome/155.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://editor.note.com",
    "Referer": "https://editor.note.com/",
})


# Authentication
response = session.get(
    "https://note.com/api/v3/notice_counts",
    timeout=30,
)

if response.status_code != 200:
    fail("Authentication failed", response)


# Create draft
response = session.post(
    "https://note.com/api/v1/text_notes",
    json={
        "body": "",
        "body_length": 0,
        "name": title,
        "index": False,
        "is_lead_form": False,
    },
    timeout=30,
)

if response.status_code not in (200, 201):
    fail("Draft creation failed", response)

note = response.json()["data"]

note_id = note["id"]
note_key = note["key"]


# Save body
response = session.post(
    (
        "https://note.com/api/v1/text_notes/"
        f"draft_save?id={note_id}&is_temp_saved=true"
    ),
    json={
        "body": body,
        "body_length": len(body),
        "name": title,
    },
    timeout=30,
)

if response.status_code not in (200, 201):
    fail("Body save failed", response)


# Upload eyecatch
headers = {
    k: v
    for k, v in session.headers.items()
    if k.lower() != "content-type"
}

with EYECATCH.open("rb") as f:
    response = requests.post(
        "https://note.com/api/v1/image_upload/note_eyecatch",
        headers=headers,
        data={"note_id": str(note_id)},
        files={
            "file": (
                "eyecatch.png",
                f,
                "image/png",
            )
        },
        timeout=60,
    )

if response.status_code not in (200, 201):
    fail("Eyecatch upload failed", response)


# Publish
payload = {
    "author_ids": [],
    "body_length": len(body),
    "circle_permissions": [],
    "disable_comment": False,
    "discount_campaigns": [],
    "exclude_ai_learning_reward": False,
    "exclude_from_creator_top": False,
    "free_body": body,
    "hashtags": hashtags,
    "image_keys": [],
    "index": False,
    "is_refund": False,
    "lead_form": {
        "is_active": False,
        "consent_url": "",
    },
    "limited": False,
    "line_add_friend": {
        "is_active": False,
        "keyword": "",
        "add_friend_url": "",
    },
    "magazine_ids": [],
    "magazine_keys": [],
    "name": title,
    "pay_body": "",
    "price": 0,
    "pro_coupon_keys": [],
    "send_notifications_flag": False,
    "separator": None,
    "status": "published",
}

response = session.put(
    f"https://note.com/api/v1/text_notes/{note_id}",
    json=payload,
    timeout=30,
)

if response.status_code not in (200, 201):
    fail("Publish failed", response)


# Public verification
response = requests.get(
    f"https://note.com/api/v3/notes/{note_key}",
    timeout=30,
)

if response.status_code != 200:
    fail("Public verification failed", response)


marker.write_text(
    json.dumps(
        {
            "target_date": target_date,
            "note_id": note_id,
            "note_key": note_key,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print("============================")
print("NOTE PUBLISH SUCCESS")
print("============================")
print("TITLE:", title)
print("NOTE KEY:", note_key)
