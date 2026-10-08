import json
from pathlib import Path
from html import escape

INPUT = Path("data/prediction/sample_v511.json")
OUTPUT = Path("output/note_article.html")

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

# -------------------------
# Publication Gate
# -------------------------

errors = []

if data.get("status") != "VALID":
    errors.append("Prediction status is not VALID")

if data.get("source_audit") != "PASS":
    errors.append("Source Audit failed")

if data.get("critical_gate") != "PASS":
    errors.append("Critical Gate failed")

if data.get("coverage", 0) < 0.90:
    errors.append("Coverage below 90%")

if errors:
    print("PUBLICATION GATE: FAILED")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("PUBLICATION GATE: PASS")

prediction_id = escape(str(data["prediction_id"]))
cutoff = escape(str(data["cutoff"]))
freeze_time = escape(str(data["freeze_time"]))
coverage = float(data["coverage"]) * 100

parts = []

parts.append("<h2>日本株 翌営業日 急騰候補</h2>")

parts.append(
    "<p>"
    "Prediction Engine v5.11による翌営業日の候補です。"
    "</p>"
)

parts.append("<h2>今回の予測情報</h2>")

parts.append(
    f"<p>Prediction ID：{prediction_id}<br>"
    f"予測基準時刻：{cutoff}<br>"
    f"データ確定時刻：{freeze_time}<br>"
    f"Coverage：{coverage:.1f}%</p>"
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

    surge = c.get("surge_score", "NA")
    limit_up = c.get("limit_up_score", "NA")
    entry = c.get("entry_score", "NA")

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
    "「買い候補」は翌営業日の寄付きからの値動きを重視して抽出しています。"
    "一方、「監視」は材料やテーマは強いものの、"
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

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(parts), encoding="utf-8")

print("ARTICLE GENERATION: PASS")
print("OUTPUT:", OUTPUT)
