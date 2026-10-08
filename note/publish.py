import json
import os
import re
import requests
from pathlib import Path
from html import escape


# ============================================================
# Configuration
# ============================================================

INPUT = Path(
    os.environ.get(
        "PREDICTION_JSON",
        "data/prediction/v59_today.json"
    )
)

PUBLISHED_DIR = Path("data/published")
EYECATCH = Path("output/eyecatch.png")

DRY_RUN = (
    os.environ.get("DRY_RUN", "true")
    .strip()
    .lower()
    in ("1", "true", "yes")
)


# ============================================================
# Utility
# ============================================================

def fail(message, response=None):
    print("")
    print("==============================")
    print("PROCESS: FAILED")
    print(message)
    print("==============================")

    if response is not None:
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text[:1500])

    raise SystemExit(1)


def clean_cookie(value):
    return value.strip().replace("\r", "").replace("\n", "")


# ============================================================
# 1. Load v5.9 article JSON
# ============================================================

if not INPUT.exists():
    fail(f"v5.9 JSON not found: {INPUT}")

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

print("v5.9 JSON: LOADED")
print("INPUT:", INPUT)


# ============================================================
# 2. Minimal v5.9 Input Check
# ============================================================

prediction_id_raw = str(
    data.get("prediction_id", "")
).strip()

title = str(
    data.get("title", "")
).strip()

body = str(
    data.get("article", "")
).strip()

if not prediction_id_raw:
    fail("Prediction ID is missing")

if not title:
    fail("Article title is missing")

if not body:
    fail("Article body is missing")

print("v5.9 INPUT CHECK: PASS")
print("PREDICTION ID:", prediction_id_raw)
print("TITLE:", title)
print("ARTICLE LENGTH:", len(body))


# ============================================================
# 3. Duplicate Protection
# ============================================================

PUBLISHED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

safe_prediction_id = re.sub(
    r"[^A-Za-z0-9._-]",
    "_",
    prediction_id_raw
)

marker_file = (
    PUBLISHED_DIR /
    f"{safe_prediction_id}.json"
)

print("DUPLICATE CHECK: START")

if marker_file.exists():

    print("==============================")
    print("DUPLICATE DETECTED")
    print("既に公開済みのPrediction IDです")
    print("note公開処理を中止します")
    print("==============================")

    raise SystemExit(0)

print("DUPLICATE CHECK: PASS")


# ============================================================
# 4. Hashtags
# ============================================================

hashtags = data.get(
    "hashtags",
    [
        "#日本株",
        "#日本株投資",
        "#株式投資",
        "#デイトレ",
        "#短期投資",
        "#株価予想",
        "#注目銘柄",
        "#急騰株",
        "#ストップ高",
        "#AI投資",
    ]
)

if not isinstance(hashtags, list):
    fail("hashtags must be a list")

hashtags = [
    str(tag).strip()
    for tag in hashtags
    if str(tag).strip()
]

hashtags = list(
    dict.fromkeys(hashtags)
)

print(
    "HASHTAGS:",
    ", ".join(hashtags)
)


# ============================================================
# 5. Pre-publication QA
# ============================================================

if not EYECATCH.exists():
    fail(f"Eyecatch not found: {EYECATCH}")

if len(body) < 100:
    fail(
        "Article body is too short. "
        "v5.9の実際の記事本文を "
        "v59_today.json の article に入れてください。"
    )

print("PRE-PUBLICATION QA: PASS")
print("EYECATCH:", EYECATCH)


# ============================================================
# 5.5 DRY RUN
# ============================================================

if DRY_RUN:
    print("")
    print("==============================")
    print("DRY RUN: SUCCESS")
    print("==============================")

    print("Prediction ID:", prediction_id_raw)
    print("Title:", title)
    print("Article Length:", len(body))
    print("Hashtags:", ", ".join(hashtags))
    print("Eyecatch:", EYECATCH)

    print("")
    print("NOTE API WAS NOT CALLED")
    print("ARTICLE WAS NOT PUBLISHED")

    raise SystemExit(0)


# ============================================================
# 6. Authentication
# ============================================================

cookie = clean_cookie(
    os.environ.get(
        "NOTE_COOKIE",
        ""
    )
)

if not cookie:
    fail("NOTE_COOKIE is empty")

session = requests.Session()

session.headers.update({
    "Cookie": cookie,

    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/155.0.0.0 "
        "Safari/537.36"
    ),

    "Accept":
        "application/json, text/plain, */*",

    "Content-Type":
        "application/json",

    "X-Requested-With":
        "XMLHttpRequest",

    "Origin":
        "https://editor.note.com",

    "Referer":
        "https://editor.note.com/",
})


# ============================================================
# 7. Authentication Check
# ============================================================

auth_response = session.get(
    "https://note.com/api/v3/notice_counts",
    timeout=30
)

print(
    "AUTH STATUS:",
    auth_response.status_code
)

if auth_response.status_code != 200:
    fail(
        "NOTE AUTHENTICATION FAILED",
        auth_response
    )

print("AUTHENTICATION: PASS")


# ============================================================
# 8. Create new draft
#
# IMPORTANT:
# この部分は今日成功した旧publish.pyと同じ。
# ============================================================

create_payload = {
    "body": "",
    "body_length": 0,
    "name": title,
    "index": False,
    "is_lead_form": False,
}

response = session.post(
    "https://note.com/api/v1/text_notes",
    json=create_payload,
    timeout=30,
)

print(
    "CREATE STATUS:",
    response.status_code
)

if response.status_code not in (
    200,
    201
):
    fail(
        "DRAFT CREATION FAILED",
        response
    )

try:
    result = response.json()
except ValueError:
    fail(
        "Invalid JSON from draft creation",
        response
    )

note_data = result.get(
    "data",
    {}
)

note_id = note_data.get("id")
note_key = note_data.get("key")

if not note_id or not note_key:
    fail(
        "note_id / note_key was not returned"
    )

print("DRAFT CREATION: PASS")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)


# ============================================================
# 9. Save article body
#
# IMPORTANT:
# 成功版を維持。
# ============================================================

save_payload = {
    "body": body,
    "body_length": len(body),
    "name": title,
}

save_url = (
    "https://note.com/api/v1/"
    "text_notes/draft_save"
    f"?id={note_id}"
    "&is_temp_saved=true"
)

response = session.post(
    save_url,
    json=save_payload,
    timeout=30,
)

print(
    "BODY SAVE STATUS:",
    response.status_code
)

if response.status_code not in (
    200,
    201
):
    fail(
        "BODY SAVE FAILED",
        response
    )

print("BODY SAVE: PASS")


# ============================================================
# 10. Upload eyecatch
#
# IMPORTANT:
# 成功版を維持。
# ============================================================

if not EYECATCH.exists():
    fail(
        f"Eyecatch not found: {EYECATCH}"
    )

multipart_headers = {
    k: v
    for k, v in session.headers.items()
    if k.lower() != "content-type"
}

with EYECATCH.open("rb") as image_file:

    files = {
        "file": (
            "eyecatch.png",
            image_file,
            "image/png"
        )
    }

    upload_response = requests.post(
        "https://note.com/api/v1/"
        "image_upload/note_eyecatch",

        headers=multipart_headers,

        data={
            "note_id": str(note_id)
        },

        files=files,

        timeout=60,
    )

print(
    "EYECATCH STATUS:",
    upload_response.status_code
)

if upload_response.status_code not in (
    200,
    201
):
    fail(
        "EYECATCH UPLOAD FAILED",
        upload_response
    )

print("EYECATCH: PASS")


# ============================================================
# 11. Final QA
# ============================================================

qa_errors = []

if not body.strip():
    qa_errors.append(
        "Article body is empty"
    )

if not title.strip():
    qa_errors.append(
        "Article title is empty"
    )

if not hashtags:
    qa_errors.append(
        "Hashtags are empty"
    )

if qa_errors:

    print("ARTICLE QA: FAILED")

    for error in qa_errors:
        print("-", error)

    raise SystemExit(1)

print("ARTICLE QA: PASS")


# ============================================================
# 12. Publish
#
# IMPORTANT:
# 今日成功した旧publish.pyのpayloadを維持。
# ============================================================

publish_payload = {
    "author_ids": [],

    "body_length":
        len(body),

    "circle_permissions": [],

    "disable_comment":
        False,

    "discount_campaigns": [],

    "exclude_ai_learning_reward":
        False,

    "exclude_from_creator_top":
        False,

    "free_body":
        body,

    "hashtags":
        hashtags,

    "image_keys": [],

    "index":
        False,

    "is_refund":
        False,

    "lead_form": {
        "is_active": False,
        "consent_url": ""
    },

    "limited":
        False,

    "line_add_friend": {
        "is_active": False,
        "keyword": "",
        "add_friend_url": ""
    },

    "magazine_ids": [],

    "magazine_keys": [],

    "name":
        title,

    "pay_body":
        "",

    "price":
        0,

    "pro_coupon_keys": [],

    "send_notifications_flag":
        False,

    "separator":
        None,

    "status":
        "published",
}

publish_url = (
    "https://note.com/api/v1/"
    f"text_notes/{note_id}"
)

publish_response = session.put(
    publish_url,
    json=publish_payload,
    timeout=30,
)

print(
    "PUBLISH STATUS:",
    publish_response.status_code
)

if publish_response.status_code not in (
    200,
    201
):
    fail(
        "NOTE PUBLISH FAILED",
        publish_response
    )

print("PUBLISH API: PASS")


# ============================================================
# 13. Public verification
# ============================================================

verify_url = (
    "https://note.com/api/v3/"
    f"notes/{note_key}"
)

verify_response = requests.get(
    verify_url,

    headers={
        "User-Agent":
            session.headers["User-Agent"],

        "Accept":
            "application/json"
    },

    timeout=30,
)

print(
    "VERIFY STATUS:",
    verify_response.status_code
)

if verify_response.status_code != 200:
    fail(
        "PUBLIC VERIFY FAILED",
        verify_response
    )

print("PUBLIC VERIFY: PASS")


# ============================================================
# 14. Publication Marker
# ============================================================

marker_data = {
    "prediction_id":
        prediction_id_raw,

    "note_id":
        note_id,

    "note_key":
        note_key,

    "status":
        "PUBLISHED",

    "engine":
        data.get(
            "engine",
            "Prediction Engine v5.9"
        ),

    "target_date":
        data.get("target_date"),
}

marker_file.write_text(
    json.dumps(
        marker_data,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(
    "PUBLICATION MARKER: CREATED"
)

print(
    "MARKER:",
    marker_file
)


# ============================================================
# SUCCESS
# ============================================================

print("")
print("==============================")
print("v5.9 → note PUBLISH: SUCCESS")
print("==============================")

print(
    "Prediction ID:",
    prediction_id_raw
)

print(
    "NOTE ID:",
    note_id
)

print(
    "NOTE KEY:",
    note_key
)
