import json
import os
import requests
from pathlib import Path
from html import escape

INPUT = Path("data/prediction/sample_v511.json")

# =========================================
# 1. Freeze JSON
# =========================================

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

# =========================================
# 2. Publication Gate
# =========================================

errors = []

if data.get("status") != "VALID":
    errors.append("Prediction status is not VALID")

if data.get("source_audit") != "PASS":
    errors.append("Source Audit failed")

if data.get("critical_gate") != "PASS":
    errors.append("Critical Gate failed")

if float(data.get("coverage", 0)) < 0.90:
    errors.append("Coverage below 90%")

if errors:
    print("PUBLICATION GATE: FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("PUBLICATION GATE: PASS")

# =========================================
# 3. Article generation
# =========================================

prediction_id = escape(str(data["prediction_id"]))
cutoff = escape(str(data["cutoff"]))
freeze_time = escape(str(data["freeze_time"]))
coverage = float(data["coverage"]) * 100

title = f"日本株 翌営業日急騰候補｜{prediction_id}"

parts = []

parts.append("<h2>日本株 翌営業日 急騰候補</h2>")

parts.append(
    "<p>"
    "Prediction Engine v5.11による翌営業日の候補です。"
    "</p>"
)

parts.append("<h2>今回の予測情報</h2>")

parts.append(
    f"<p>"
    f"Prediction ID：{prediction_id}<br>"
    f"予測基準時刻：{cutoff}<br>"
    f"データ確定時刻：{freeze_time}<br>"
    f"Coverage：{coverage:.1f}%"
    f"</p>"
)

parts.append("<h2>買い候補・監視銘柄</h2>")

for c in data.get("candidates", []):

    rank = escape(str(c.get("rank", "")))
    code = escape(str(c.get("code", "")))
    name = escape(str(c.get("name", "")))
    decision = escape(str(c.get("decision", "")))
    risk = escape(str(c.get("risk", "")))
    reason = escape(str(c.get("reason", "")))

    previous_close = int(c.get("previous_close", 0))
    required_capital = int(c.get("required_capital", 0))

    surge = escape(str(c.get("surge_score", "NA")))
    limit_up = escape(str(c.get("limit_up_score", "NA")))
    entry = escape(str(c.get("entry_score", "NA")))

    parts.append(
        f"<h3>{rank}位　{code} {name}</h3>"
        f"<p><strong>判定：{decision}</strong></p>"
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

parts.append("<h2>この予測の見方</h2>")

parts.append(
    "<p>"
    "「買い候補」は翌営業日の寄付きからの値動きを重視しています。"
    "「監視」は材料やテーマは強いものの、"
    "高値追い・流動性・下落リスクなどから慎重な判断が必要な銘柄です。"
    "</p>"
)

parts.append("<h2>注意事項</h2>")

parts.append(
    "<p>"
    "本記事は公開情報を基にした分析・検証を目的とするものであり、"
    "特定銘柄の売買を推奨するものではありません。"
    "株式投資には価格変動による損失の可能性があります。"
    "最終的な投資判断はご自身で行ってください。"
    "</p>"
)

body = "\n".join(parts)

print("ARTICLE GENERATION: PASS")

# =========================================
# 4. note authentication
# =========================================

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

# =========================================
# 5. Create draft
# =========================================

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
    print("DRAFT CREATION: FAILED")
    print("RESPONSE:", response.text[:1000])
    raise SystemExit(1)

result = response.json()
note_data = result.get("data", {})

note_id = note_data.get("id")
note_key = note_data.get("key")

if not note_id:
    raise RuntimeError("note_id was not returned")

print("DRAFT CREATION: PASS")
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)

# =========================================
# 6. Save body
# =========================================

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

print("")
print("==============================")
print("v5.11 → note DRAFT: SUCCESS")
print("==============================")
print("Prediction ID:", prediction_id)
print("NOTE ID:", note_id)
print("NOTE KEY:", note_key)
