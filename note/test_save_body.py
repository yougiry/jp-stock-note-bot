import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

cookie = os.environ.get("NOTE_COOKIE", "")
cookie = cookie.strip().replace("\r", "").replace("\n", "")

if not cookie:
    raise RuntimeError("NOTE_COOKIE is empty")

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

session = requests.Session()
session.headers.update(headers)

now = datetime.now(ZoneInfo("Asia/Tokyo"))

title = f"株式予測APIテスト - {now:%Y-%m-%d %H:%M}"

# -------------------------
# 1. 下書きを新規作成
# -------------------------

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

print("CREATE STATUS:", response.status_code)

if response.status_code not in (200, 201):
    print("CREATE: FAILED")
    print("RESPONSE:", response.text[:1000])
    raise SystemExit(1)

result = response.json()
data = result.get("data", {})

note_id = data.get("id")
note_key = data.get("key")

if not note_id:
    raise RuntimeError("note_id was not returned")

print("CREATE: PASS")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)

# -------------------------
# 2. テスト本文
# -------------------------

body = """
<h2>日本株 翌営業日予測テスト</h2>

<p>これはGitHub Actionsから自動生成したテスト記事です。</p>

<h2>本日の判定</h2>

<p><strong>買い候補</strong></p>

<p>5932 三協立山</p>

<p>前日終値：629円</p>

<p>100株必要額：62,900円</p>

<p>判定：買い候補</p>

<h2>注意事項</h2>

<p>本記事はPrediction Engine v5.11の自動投稿システム開発用テストです。</p>

<p>投資判断はご自身の責任で行ってください。</p>
""".strip()

# -------------------------
# 3. 本文を下書き保存
# -------------------------

save_payload = {
    "body": body,
    "body_length": len(body),
    "name": title,
}

save_url = (
    "https://note.com/api/v1/text_notes/"
    f"draft_save?id={note_id}&is_temp_saved=true"
)

response = session.post(
    save_url,
    json=save_payload,
    timeout=30,
)

print("SAVE STATUS:", response.status_code)

if response.status_code not in (200, 201):
    print("BODY SAVE: FAILED")
    print("RESPONSE:", response.text[:1000])
    raise SystemExit(1)

print("BODY SAVE: PASS")
print("TITLE:", title)
print("NOTE KEY:", note_key)
