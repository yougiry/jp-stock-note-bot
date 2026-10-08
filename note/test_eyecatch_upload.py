import os
import requests
from pathlib import Path

IMAGE = Path("output/eyecatch.png")

if not IMAGE.exists():
    raise RuntimeError("output/eyecatch.png not found")

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
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://editor.note.com",
    "Referer": "https://editor.note.com/",
})

# ==========================================
# 1. テスト下書き作成
# ==========================================

title = "EYECATCH API TEST - DELETE ME"

create_response = session.post(
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

print("CREATE STATUS:", create_response.status_code)

if create_response.status_code not in (200, 201):
    print("CREATE FAILED")
    print(create_response.text[:1000])
    raise SystemExit(1)

data = create_response.json().get("data", {})

note_id = data.get("id")
note_key = data.get("key")

if not note_id:
    raise RuntimeError("note_id was not returned")

print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)

# ==========================================
# 2. 本文保存
# ==========================================

body = (
    "<h2>アイキャッチ自動設定テスト</h2>"
    "<p>GitHub Actionsから生成した1280×670画像を"
    "自動設定するためのテスト記事です。</p>"
)

save_response = session.post(
    "https://note.com/api/v1/text_notes/"
    f"draft_save?id={note_id}&is_temp_saved=true",
    json={
        "body": body,
        "body_length": len(body),
        "name": title,
    },
    timeout=30,
)

print("BODY SAVE STATUS:", save_response.status_code)

if save_response.status_code not in (200, 201):
    print("BODY SAVE FAILED")
    print(save_response.text[:1000])
    raise SystemExit(1)

# ==========================================
# 3. Eyecatch upload
# ==========================================

upload_url = "https://note.com/api/v1/image_upload/note_eyecatch"

# multipartではContent-Typeをrequestsに生成させる
with IMAGE.open("rb") as image_file:

    files = {
        "file": (
            "eyecatch.png",
            image_file,
            "image/png"
        )
    }

    upload_response = session.post(
        upload_url,
        data={
            "note_id": str(note_id)
        },
        files=files,
        timeout=60,
    )

print("EYECATCH STATUS:", upload_response.status_code)

if upload_response.status_code not in (200, 201):
    print("EYECATCH UPLOAD: FAILED")
    print(upload_response.text[:1000])
    raise SystemExit(1)

print("EYECATCH UPLOAD: PASS")
print("==============================")
print("EYECATCH TEST: SUCCESS")
print("==============================")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)
