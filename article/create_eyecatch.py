import json
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

INPUT = Path("data/prediction/sample_v511.json")
OUTPUT = Path("output/eyecatch.png")

WIDTH = 1280
HEIGHT = 670

# =========================================
# 1. Prediction JSON
# =========================================

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

prediction_id = str(data["prediction_id"])
candidates = data.get("candidates", [])

buy_count = sum(
    1 for c in candidates
    if c.get("decision") == "買い候補"
)

# Prediction IDから日付を取得
try:
    date_text = prediction_id.split("-")[1]
    dt = datetime.strptime(date_text, "%Y%m%d")
    display_date = dt.strftime("%Y.%m.%d")
except Exception:
    display_date = "DATE UNKNOWN"

# =========================================
# 2. Canvas
# =========================================

img = Image.new(
    "RGB",
    (WIDTH, HEIGHT),
    (15, 23, 42)
)

draw = ImageDraw.Draw(img)

# =========================================
# 3. Fonts
# =========================================

import subprocess


def find_japanese_font():
    """
    fontconfig に日本語対応フォントを問い合わせ、
    実際にインストールされているフォントファイルを取得する。
    """

    commands = [
        ["fc-match", "-f", "%{file}", "Noto Sans CJK JP"],
        ["fc-match", "-f", "%{file}", "Noto Sans JP"],
        ["fc-match", "-f", "%{file}", ":lang=ja"],
    ]

    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )

            path = result.stdout.strip()

            if path and Path(path).exists():
                print("FONT DETECTED:", path)
                return path

        except Exception as e:
            print("FONT SEARCH FAILED:", command, e)

    raise RuntimeError(
        "Japanese font could not be detected by fontconfig"
    )


font_path = find_japanese_font()

font_small = ImageFont.truetype(font_path, 32)
font_medium = ImageFont.truetype(font_path, 48)
font_large = ImageFont.truetype(font_path, 78)
font_xlarge = ImageFont.truetype(font_path, 92)

# =========================================
# 4. Header
# =========================================

draw.text(
    (75, 65),
    "Prediction Engine v5.11",
    font=font_small,
    fill=(150, 180, 220)
)

draw.text(
    (75, 135),
    "日本株",
    font=font_large,
    fill=(255, 255, 255)
)

draw.text(
    (75, 235),
    "翌営業日 急騰候補",
    font=font_xlarge,
    fill=(255, 255, 255)
)

# =========================================
# 5. Divider
# =========================================

draw.rectangle(
    (75, 370, 1205, 374),
    fill=(80, 140, 255)
)

# =========================================
# 6. Date / candidate count
# =========================================

draw.text(
    (75, 420),
    display_date,
    font=font_medium,
    fill=(220, 225, 235)
)

draw.text(
    (75, 500),
    f"買い候補 {buy_count}銘柄",
    font=font_medium,
    fill=(255, 215, 90)
)

# =========================================
# 7. Footer
# =========================================

draw.text(
    (75, 605),
    "AI × Catalyst × Theme × Flow × Risk",
    font=font_small,
    fill=(140, 150, 170)
)

# =========================================
# 8. Save
# =========================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

img.save(
    OUTPUT,
    format="PNG",
    optimize=True
)

# =========================================
# 9. Verification
# =========================================

with Image.open(OUTPUT) as check:
    if check.size != (1280, 670):
        raise RuntimeError(
            f"Invalid eyecatch size: {check.size}"
        )

    print("EYECATCH GENERATION: PASS")
    print("SIZE:", check.size)
    print("FORMAT:", check.format)
    print("OUTPUT:", OUTPUT)
    print("Prediction ID:", prediction_id)
    print("買い候補:", buy_count)
