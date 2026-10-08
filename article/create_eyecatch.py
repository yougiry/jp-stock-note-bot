from pathlib import Path
import json
import re
from datetime import datetime

INPUT = Path("data/prediction/v59_result.md")
OUTPUT = Path("output/article.md")
META = Path("output/article_meta.json")


def extract_target_date(text):
    patterns = [
        r"対象(?:営業)?日[：:]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        r"Target Date[：:]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).replace("/", "-")

    return ""


def build_article(result):
    target_date = extract_target_date(result)

    title_date = ""
    if target_date:
        try:
            d = datetime.strptime(target_date, "%Y-%m-%d")
            title_date = f"【{d.year}年{d.month}月{d.day}日版】"
        except ValueError:
            pass

    title = (
        "明日の日本株、急騰・ストップ高候補を分析"
        "――Prediction Engine v5.9 "
        + title_date
    )

    intro = """# {title}

日本株の翌営業日の急騰・ストップ高候補について、
Prediction Engine v5.9で分析した。

今回も単純な「好材料銘柄一覧」ではなく、

- 材料の強さ
- 業績へのインパクト
- 株価モメンタム
- 出来高・需給
- PTSでの反応
- 流動性
- 下落リスク
- 翌朝の寄り付き条件

を含めて判断する。

特に重要なのは、

**「材料が強い銘柄」と「今から買いやすい銘柄」は同じではない**

という点だ。

以下は、今回のPrediction Engine v5.9の実行結果である。

---

""".format(title=title)

    ending = """

---

# 翌朝に確認するポイント

今回の候補についても、最終的な判断では翌朝の価格形成が重要になる。

特に確認したいのは、

1. 前日終値からのギャップ率
2. 寄り付き前の気配
3. 寄り付き直後の出来高
4. 始値を維持できるか
5. 高値更新時に出来高を伴っているか
6. 市場全体の地合い

の6項目だ。

好材料が出ても、大幅なギャップアップですでに材料を織り込んでいる場合、そこからの期待値は低下する。

逆に材料が強く、価格への織り込みが限定的で、出来高を伴って買われる場合は翌営業日の注目度が高くなる。

Prediction Engine v5.9では、この違いを重視している。

---

## この分析について

本記事はPrediction Engine v5.9の実行結果を読みやすい形に編集したものです。

確認できない数値や確率を推測で補完することは行っていません。

本記事は公開情報を基にした分析・検証を目的とするもので、特定銘柄の売買を推奨するものではありません。

株式投資には価格変動による損失の可能性があります。最終的な投資判断はご自身で行ってください。
"""

    article = intro + result.strip() + ending

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
        "#決算",
        "#上方修正",
        "#AI投資",
    ]

    return title, target_date, article, hashtags


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"v5.9 result not found: {INPUT}"
        )

    result = INPUT.read_text(encoding="utf-8").strip()

    if len(result) < 500:
        raise RuntimeError(
            "v5.9 result is too short. Article generation stopped."
        )

    title, target_date, article, hashtags = build_article(result)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(article, encoding="utf-8")

    META.write_text(
        json.dumps(
            {
                "title": title,
                "target_date": target_date,
                "hashtags": hashtags,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("ARTICLE CREATED")
    print("TITLE:", title)
    print("TARGET:", target_date)
    print("LENGTH:", len(article))
    print("OUTPUT:", OUTPUT)


if __name__ == "__main__":
    main()
