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
        "data/prediction/sample_v511.json"
    )
)

PUBLISHED_DIR = Path("data/published")
EYECATCH = Path("output/eyecatch.png")

MIN_COVERAGE = 0.90

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
# 1. Load frozen Prediction JSON
# ============================================================

if not INPUT.exists():
    fail(f"Prediction JSON not found: {INPUT}")

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

print("PREDICTION JSON: LOADED")
print("INPUT:", INPUT)


# ============================================================
# 2. Publication Gate
# ============================================================

errors = []

if data.get("status") != "VALID":
    errors.append("Prediction status is not VALID")

if data.get("source_audit") != "PASS":
    errors.append("Source Audit is not PASS")

if data.get("critical_gate") != "PASS":
    errors.append("Critical Gate is not PASS")

# Formal v5.11 supports explicit freeze_status.
# During migration, missing field is reported separately below.
freeze_status = data.get("freeze_status")

if freeze_status is not None and freeze_status != "PASS":
    errors.append("Freeze Status is not PASS")

try:
    coverage = float(data.get("coverage", 0))
except (TypeError, ValueError):
    coverage = 0
    errors.append("Coverage is invalid")

if coverage < MIN_COVERAGE:
    errors.append(
        f"Coverage below {MIN_COVERAGE * 100:.0f}%"
    )

prediction_id_raw = str(
    data.get("prediction_id", "")
).strip()

if not prediction_id_raw:
    errors.append("Prediction ID is missing")

if not data.get("cutoff"):
    errors.append("Prediction cutoff is missing")

if not data.get("freeze_time"):
    errors.append("Freeze time is missing")

if not isinstance(data.get("candidates"), list):
    errors.append("Candidates is not a list")

if errors:
    print("PUBLICATION GATE: FAILED")

    for error in errors:
        print("-", error)

    raise SystemExit(1)

print("PUBLICATION GATE: PASS")

if data.get("freeze_status") != "PASS":
    errors.append("Freeze Status is not PASS")


# ============================================================
# 3. Duplicate Protection
# ============================================================

PUBLISHED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# Filesystem-safe ID.
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
print("Prediction ID:", prediction_id_raw)

if marker_file.exists():

    print("==============================")
    print("DUPLICATE DETECTED")
    print("既に公開済みのPrediction IDです")
    print("note公開処理を中止します")
    print("==============================")

    raise SystemExit(0)

print("DUPLICATE CHECK: PASS")


# ============================================================
# 4. Article generation
# ============================================================

prediction_id_html = escape(
    prediction_id_raw
)

cutoff_html = escape(
    str(data["cutoff"])
)

freeze_time_html = escape(
    str(data["freeze_time"])
)

coverage_percent = coverage * 100

title = (
    "日本株 翌営業日急騰候補｜"
    f"{prediction_id_raw}"
)

parts = []

parts.append(
    "<h2>日本株 翌営業日 急騰候補</h2>"
)

parts.append(
    "<p>"
    "Prediction Engine v5.11による"
    "翌営業日の候補です。"
    "</p>"
)

parts.append(
    "<h2>今回の予測情報</h2>"
)

parts.append(
    "<p>"
    f"Prediction ID：{prediction_id_html}<br>"
    f"予測基準時刻：{cutoff_html}<br>"
    f"データ確定時刻：{freeze_time_html}<br>"
    f"Coverage：{coverage_percent:.1f}%"
    "</p>"
)

parts.append(
    "<h2>買い候補・監視銘柄</h2>"
)

for c in data.get("candidates", []):

    rank = escape(
        str(c.get("rank", ""))
    )

    code = escape(
        str(c.get("code", ""))
    )

    name = escape(
        str(c.get("name", ""))
    )

    decision = escape(
        str(c.get("decision", ""))
    )

    risk = escape(
        str(c.get("risk", ""))
    )

    reason = escape(
        str(c.get("reason", ""))
    )

    previous_close = int(
        c.get("previous_close", 0) or 0
    )

    required_capital = int(
        c.get("required_capital", 0) or 0
    )

    surge = escape(
        str(c.get("surge_score", "NA"))
    )

    limit_up = escape(
        str(c.get("limit_up_score", "NA"))
    )

    entry = escape(
        str(c.get("entry_score", "NA"))
    )

    parts.append(
        f"<h3>{rank}位　{code} {name}</h3>"

        f"<p>"
        f"<strong>判定：{decision}</strong>"
        f"</p>"

        f"<p>"
        f"前日終値：{previous_close:,}円<br>"
        f"100株必要額：約{required_capital:,}円<br>"
        f"急騰スコア：{surge}<br>"
        f"ストップ高スコア：{limit_up}<br>"
        f"寄付きエントリースコア：{entry}<br>"
        f"リスク：{risk}"
        f"</p>"

        f"<p>{reason}</p>"
    )


parts.append(
    "<h2>この予測の見方</h2>"
)

parts.append(
    "<p>"
    "「買い候補」は翌営業日の寄付きからの"
    "値動きを重視しています。"
    "「監視」は材料やテーマは強いものの、"
    "高値追い・流動性・下落リスクなどから"
    "慎重な判断が必要な銘柄です。"
    "</p>"
)

parts.append(
    "<h2>注意事項</h2>"
)

parts.append(
    "<p>"
    "本記事は公開情報を基にした"
    "分析・検証を目的とするものであり、"
    "特定銘柄の売買を推奨するものではありません。"
    "株式投資には価格変動による"
    "損失の可能性があります。"
    "最終的な投資判断はご自身で行ってください。"
    "</p>"
)

body = "\n".join(parts)

print("ARTICLE GENERATION: PASS")


# ============================================================
# 5. Hashtags
# ============================================================

hashtags = [
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

for candidate in data.get(
    "candidates",
    []
):
    code = str(
        candidate.get("code", "")
    ).strip()

    if code:
        hashtags.append(
            f"#{code}"
        )

# Preserve order / remove duplicates.
hashtags = list(
    dict.fromkeys(hashtags)
)

print(
    "HASHTAGS:",
    ", ".join(hashtags)
)

# ============================================================
# 5.5 Pre-publication QA / DRY RUN
# ============================================================

if not EYECATCH.exists():
    fail(f"Eyecatch not found: {EYECATCH}")

if not title.strip():
    fail("Article title is empty")

if not body.strip():
    fail("Article body is empty")

if prediction_id_raw not in body:
    fail("Prediction ID missing from article")

print("PRE-PUBLICATION QA: PASS")

if DRY_RUN:
    print("")
    print("==============================")
    print("DRY RUN: SUCCESS")
    print("==============================")
    print("Prediction ID:", prediction_id_raw)
    print("Title:", title)
    print("Coverage:", f"{coverage_percent:.1f}%")
    print("Candidates:", len(data.get("candidates", [])))
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
# ============================================================

if not EYECATCH.exists():
    fail(
        f"Eyecatch not found: {EYECATCH}"
    )

# Remove JSON content-type for multipart.
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

if prediction_id_raw not in body:
    qa_errors.append(
        "Prediction ID missing from article"
    )

if qa_errors:

    print("ARTICLE QA: FAILED")

    for error in qa_errors:
        print("-", error)

    raise SystemExit(1)

print("ARTICLE QA: PASS")


# ============================================================
# 12. Publish
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

    # Avoid notifying followers during
    # initial production verification.
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

# IMPORTANT:
# Marker is created only AFTER:
#
# publish PASS
# AND
# public verification PASS

marker_data = {
    "prediction_id":
        prediction_id_raw,

    "note_id":
        note_id,

    "note_key":
        note_key,

    "status":
        "PUBLISHED",

    "cutoff":
        data.get("cutoff"),

    "freeze_time":
        data.get("freeze_time"),

    "coverage":
        coverage,
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
print("v5.11 → note PUBLISH: SUCCESS")
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
