import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

META = Path("output/article_meta.json")
OUTPUT = Path("output/eyecatch.png")

WIDTH = 1280
HEIGHT = 670


def font(size, bold=False):
    paths = []

    if bold:
        paths.append(
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        )

    paths += [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    target = meta.get("target_date", "")

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (12, 18, 32),
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (0, 0, WIDTH, 16),
        fill=(210, 45, 45),
    )

    draw.rectangle(
        (80, 135, 95, 535),
        fill=(210, 45, 45),
    )

    draw.text(
        (125, 110),
        "日本個別株",
        font=font(48, True),
        fill="white",
    )

    draw.text(
        (125, 200),
        "翌営業日",
        font=font(82, True),
        fill="white",
    )

    draw.text(
        (125, 305),
        "急騰 ＋ ストップ高候補",
        font=font(74, True),
        fill="white",
    )

    draw.text(
        (125, 435),
        "Prediction Engine v5.11",
        font=font(38),
        fill=(190, 200, 215),
    )

    if target:
        draw.text(
            (125, 510),
            f"TARGET  {target}",
            font=font(38),
            fill="white",
        )

    draw.text(
        (125, 590),
        "Catalyst / Price / Flow / Risk",
        font=font(30),
        fill=(155, 165, 180),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)

    print("EYECATCH CREATED:", OUTPUT)


if __name__ == "__main__":
    main()
