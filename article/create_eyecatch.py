import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 670

INPUT = Path(
    os.environ.get(
        "PREDICTION_JSON",
        "data/prediction/v59_today.json",
    )
)

OUTPUT = Path("output/eyecatch.png")


def load_font(size, bold=False):
    candidates = []

    if bold:
        candidates.extend([
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        ])

    candidates.extend([
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ])

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Prediction JSON not found: {INPUT}"
        )

    data = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    target_date = data.get("target_date", "")
    engine = data.get(
        "engine",
        "Prediction Engine v5.9"
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (12, 18, 32),
    )

    draw = ImageDraw.Draw(image)

    # Accent lines
    draw.rectangle(
        (0, 0, WIDTH, 16),
        fill=(210, 45, 45),
    )

    draw.rectangle(
        (80, 135, 95, 535),
        fill=(210, 45, 45),
    )

    font_small = load_font(34)
    font_medium = load_font(48, bold=True)
    font_large = load_font(82, bold=True)
    font_date = load_font(38)

    draw.text(
        (125, 120),
        "日本個別株",
        font=font_medium,
        fill=(220, 225, 235),
    )

    draw.text(
        (125, 205),
        "翌営業日",
        font=font_large,
        fill=(255, 255, 255),
    )

    draw.text(
        (125, 310),
        "急騰 ＋ ストップ高候補",
        font=font_large,
        fill=(255, 255, 255),
    )

    draw.text(
        (125, 440),
        engine,
        font=font_small,
        fill=(185, 195, 210),
    )

    if target_date:
        draw.text(
            (125, 510),
            f"TARGET  {target_date}",
            font=font_date,
            fill=(235, 235, 235),
        )

    draw.text(
        (125, 590),
        "Prediction / EEV / Downside Risk",
        font=font_small,
        fill=(155, 165, 180),
    )

    image.save(
        OUTPUT,
        format="PNG",
        optimize=True,
    )

    print("==============================")
    print("EYECATCH GENERATED")
    print("==============================")
    print("INPUT :", INPUT)
    print("OUTPUT:", OUTPUT)
    print("SIZE  :", image.size)


if __name__ == "__main__":
    main()
