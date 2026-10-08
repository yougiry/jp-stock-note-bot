import json
import sys
from pathlib import Path


INPUT = Path(
    "data/market/jquants/2026-07-16.json"
)

OUTPUT_DIR = Path(
    "data/market/normalized"
)


def fail(message):
    print("")
    print("==============================")
    print("PRICE NORMALIZATION: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    # J-Quants v2 5-character code
    # -> JPX 4-character code
    if len(code) == 5:
        code = code[:4]

    return code


def number(value):
    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def main():

    if not INPUT.exists():
        fail(
            f"Input not found: {INPUT}"
        )

    with INPUT.open(
        "r",
        encoding="utf-8",
    ) as f:
        payload = json.load(f)

    rows = payload.get(
        "rows",
        []
    )

    if not rows:
        fail(
            "No price rows"
        )

    normalized = []

    invalid = 0

    for row in rows:

        code = normalize_code(
            row.get("Code", "")
        )

        date = row.get("Date")

        if not code or not date:
            invalid += 1
            continue

        item = {
            "date":
                date,

            "code":
                code,

            "open":
                number(row.get("O")),

            "high":
                number(row.get("H")),

            "low":
                number(row.get("L")),

            "close":
                number(row.get("C")),

            "volume":
                number(row.get("Vo")),

            "trading_value":
                number(row.get("Va")),

            "adjustment_factor":
                number(row.get("AdjFactor")),

            "adjusted_open":
                number(row.get("AdjO")),

            "adjusted_high":
                number(row.get("AdjH")),

            "adjusted_low":
                number(row.get("AdjL")),

            "adjusted_close":
                number(row.get("AdjC")),

            "adjusted_volume":
                number(row.get("AdjVo")),

            "market_cap":
                number(row.get("MktCap")),

            "ex_rights_type":
                row.get("ExRT"),

            "upper_limit":
                number(row.get("UL")),

            "lower_limit":
                number(row.get("LL")),

            "source":
                "J-Quants",
        }

        normalized.append(
            item
        )

    if not normalized:
        fail(
            "Normalization produced zero rows"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_date = normalized[0]["date"]

    output = (
        OUTPUT_DIR /
        f"{target_date}.json"
    )

    result = {
        "date":
            target_date,

        "source":
            "J-Quants",

        "schema":
            "v511-market-v1",

        "rows":
            normalized,
    }

    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    print("")
    print("==============================")
    print("PRICE NORMALIZATION: PASS")
    print("==============================")

    print(
        "Input rows:",
        len(rows)
    )

    print(
        "Normalized rows:",
        len(normalized)
    )

    print(
        "Invalid rows:",
        invalid
    )

    print(
        "Output:",
        output
    )

    print("")
    print("SAMPLE:")

    for row in normalized[:3]:
        print(row)


if __name__ == "__main__":
    main()
