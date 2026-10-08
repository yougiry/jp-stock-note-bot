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

import glob

font_patterns = [
    "/usr/share/fonts/**/*NotoSansCJK*.ttc",
    "/usr/share/fonts/**/*NotoSansCJK*.otf",
    "/usr/share/fonts/**/*NotoSansJP*.ttf",
    "/usr/share/fonts/**/*NotoSansJP*.otf",
]

font_files = []

for pattern in font_patterns:
    font_files.extend(
        glob.glob(pattern, recursive=True)
    )

if not font_files:
    raise RuntimeError(
        "Japanese Noto font file not found. "
        "Check fonts-noto-cjk installation."
    )

# Boldを優先
bold_fonts = [
    path for path in font_files
    if "Bold" in Path(path).name
]

if bold_fonts:
    font_path = sorted(bold_fonts)[0]
else:
    font_path = sorted(font_files)[0]

print("JAPANESE FONT:", font_path)

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
