import json
import os
from pathlib import Path

INPUT = Path(os.environ.get("PREDICTION_JSON", ""))
ARTICLE = Path("output/article.md")
META = Path("output/article_meta.json")


def fail(msg):
    raise SystemExit(msg)


def main():
    if not str(INPUT) or not INPUT.exists():
        fail(f"Prediction JSON not found: {INPUT}")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    if data.get("status") != "VALID" or data.get("freeze_status") != "PASS":
        fail("Frozen prediction is not publishable")
    if float(data.get("coverage", 0)) < 0.90:
        fail("Coverage below 90%")

    target = data.get("target_date") or str(data.get("cutoff", ""))[:10]
    title = f"日本株 翌営業日 急騰候補｜{target}｜Prediction Engine v5.11"
    lines = [
        "## 日本株 翌営業日 急騰候補",
        "",
        "Prediction Engine v5.11の価格・出来高・流動性・リスク・時価総額スクリーニング結果です。",
        "現在の実装では材料・TDnet・PTS・テーマ評価は正式スコアに未接続のため、確率ではなくランキングスコアとして表示します。",
        "",
        f"Prediction ID：{data['prediction_id']}  ",
        f"予測基準時刻：{data['cutoff']}  ",
        f"Coverage：{float(data['coverage'])*100:.1f}%",
        "",
        "## 候補銘柄",
    ]
    for c in data.get("candidates", []):
        lines += [
            "",
            f"### {c['rank']}位　{c['code']} {c['name']}",
            f"判定：**{c['decision']}**  ",
            f"前日終値：{float(c.get('previous_close',0)):,.0f}円  ",
            f"100株必要額：約{int(c.get('required_capital',0)):,}円  ",
            f"ランキングスコア：{c.get('surge_score','NA')}  ",
            f"リスク：{c.get('risk','NA')}  ",
            str(c.get("reason", "")),
        ]
    lines += [
        "", "## 注意事項", "",
        "本記事は公開情報を基にした分析・検証用で、特定銘柄の売買を推奨するものではありません。最終的な投資判断はご自身で行ってください。",
    ]
    ARTICLE.parent.mkdir(parents=True, exist_ok=True)
    ARTICLE.write_text("\n".join(lines), encoding="utf-8")
    META.write_text(json.dumps({
        "title": title,
        "hashtags": ["日本株", "株式投資", "株価予測", "AI", "データ分析"],
        "target_date": target,
        "prediction_id": data["prediction_id"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PRODUCTION ARTICLE: PASS", ARTICLE)


if __name__ == "__main__":
    main()
