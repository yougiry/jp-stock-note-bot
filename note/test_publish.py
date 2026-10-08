import os
import requests

# =========================================
# Configuration
# =========================================

TITLE = "NOTE API PUBLISH TEST - DELETE ME"

BODY = """
<h2>note自動公開APIテスト</h2>
<p>GitHub Actionsから作成した自動公開テスト記事です。</p>
<p>このテスト記事は削除して問題ありません。</p>
""".strip()

HASHTAGS = [
    "#日本株",
    "#株式投資",
    "#AI",
]

# =========================================
# Authentication
# =========================================

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
        "Chrome/155.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://editor.note.com",
    "Referer": "https://editor.note.com/",
})

# =========================================
# 1. Create draft
# =========================================

create_response = session.post(
    "https://note.com/api/v1/text_notes",
    json={
        "body": "",
        "body_length": 0,
        "name": TITLE,
        "index": False,
        "is_lead_form": False,
    },
    timeout=30,
)

print("CREATE STATUS:", create_response.status_code)

if create_response.status_code not in (200, 201):
    print(create_response.text[:1000])
    raise SystemExit(1)

created = create_response.json().get("data", {})

note_id = created.get("id")
note_key = created.get("key")

if not note_id or not note_key:
    raise RuntimeError("note id/key not returned")

print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)

# =========================================
# 2. Save draft body
# =========================================

save_response = session.post(
    (
        "https://note.com/api/v1/text_notes/"
        f"draft_save?id={note_id}&is_temp_saved=true"
    ),
    json={
        "body": BODY,
        "body_length": len(BODY),
        "name": TITLE,
    },
    timeout=30,
)

print("BODY SAVE STATUS:", save_response.status_code)

if save_response.status_code not in (200, 201):
    print(save_response.text[:1000])
    raise SystemExit(1)

# =========================================
# 3. Publish
# =========================================

publish_payload = {
    "author_ids": [],
    "body_length": len(BODY),
    "circle_permissions": [],
    "disable_comment": False,
    "discount_campaigns": [],
    "exclude_ai_learning_reward": False,
    "exclude_from_creator_top": False,

    "free_body": BODY,

    "hashtags": HASHTAGS,

    "image_keys": [],
    "index": False,
    "is_refund": False,

    "lead_form": {
        "is_active": False,
        "consent_url": ""
    },

    "limited": False,

    "line_add_friend": {
        "is_active": False,
        "keyword": "",
        "add_friend_url": ""
    },

    "magazine_ids": [],
    "magazine_keys": [],

    "name": TITLE,

    "pay_body": "",
    "price": 0,

    "pro_coupon_keys": [],

    "send_notifications_flag": False,

    "separator": None,

    "status": "published",
}

publish_url = (
    f"https://note.com/api/v1/text_notes/{note_id}"
)

publish_response = session.put(
    publish_url,
    json=publish_payload,
    timeout=30,
)

print("PUBLISH STATUS:", publish_response.status_code)

if publish_response.status_code not in (200, 201):
    print("PUBLISH: FAILED")
    print(publish_response.text[:1500])
    raise SystemExit(1)

print("PUBLISH API: PASS")

# =========================================
# 4. Verify public article
# =========================================

verify_url = (
    f"https://note.com/api/v3/notes/{note_key}"
)

verify_response = requests.get(
    verify_url,
    headers={
        "User-Agent": session.headers["User-Agent"],
        "Accept": "application/json",
    },
    timeout=30,
)

print("VERIFY STATUS:", verify_response.status_code)

if verify_response.status_code != 200:
    print("PUBLIC VERIFY: FAILED")
    print(verify_response.text[:1000])
    raise SystemExit(1)

print("PUBLIC VERIFY: PASS")

print("")
print("==============================")
print("NOTE PUBLISH TEST: SUCCESS")
print("==============================")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)
print("PUBLIC URL:")
print(f"https://note.com/{note_key}")
