import json
import sys
from pathlib import Path

from collect_universe import collect_jpx_universe


PRICE_FILE = Path(
    "data/market/jquants/2026-07-16.json"
)

MIN_COVERAGE = 0.90


def fail(message):
    print("")
    print("==============================")
    print("PRICE COVERAGE: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


def normalize_code(value):
    """
    Normalize JPX/J-Quants security codes
    to JPX 4-character format.

    Examples:
        72030 -> 7203
        13010 -> 1301
        130A0 -> 130A
        7203  -> 7203
        130A  -> 130A
    """

    code = str(value).strip().upper()

    # Excel numeric representation
    if code.endswith(".0"):
        code = code[:-2]

    # J-Quants v2 uses 5-character codes.
    # Final character is removed for comparison
    # with JPX 4-character security codes.
    if len(code) == 5:
        code = code[:4]

    return code


# ==========================================
# J-Quants data
# ==========================================

if not PRICE_FILE.exists():
    fail(
        f"Price file not found: {PRICE_FILE}"
    )

with PRICE_FILE.open(
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
        "J-Quants price rows are empty"
    )


print("")
print("==============================")
print("PRICE COVERAGE CHECK")
print("==============================")

print(
    "J-Quants rows:",
    len(rows)
)


# ==========================================
# Detect actual Code field
# ==========================================

sample = rows[0]

print("")
print("J-Quants fields:")

for key in sample.keys():
    print(
        " -",
        key
    )


code_candidates = [
    "Code",
    "code",
    "LocalCode",
    "local_code",
]

code_field = None

for candidate in code_candidates:

    if candidate in sample:
        code_field = candidate
        break


if code_field is None:
    fail(
        "Stock-code field could not be detected"
    )


print("")
print(
    "Detected code field:",
    code_field
)


price_codes = set()

for row in rows:

    value = row.get(
        code_field
    )

    if value is None:
        continue

    code = normalize_code(
        value
    )

    if code:
        price_codes.add(
            code
        )


print(
    "Unique price codes:",
    len(price_codes)
)


# ==========================================
# JPX Universe
# ==========================================

print("")
print("Loading JPX universe...")


universe = collect_jpx_universe()


if not universe:
    fail(
        "JPX universe is empty"
    )


universe_codes = {
    normalize_code(
        stock["code"]
    )
    for stock in universe
}


print(
    "JPX universe:",
    len(universe_codes)
)


# ==========================================
# Coverage
# ==========================================

matched = (
    universe_codes
    &
    price_codes
)

missing = (
    universe_codes
    -
    price_codes
)

extra = (
    price_codes
    -
    universe_codes
)


coverage = (
    len(matched)
    /
    len(universe_codes)
)


print("")
print("==============================")
print("COVERAGE RESULT")
print("==============================")

print(
    "JPX Universe:",
    len(universe_codes)
)

print(
    "Price codes:",
    len(price_codes)
)

print(
    "Matched:",
    len(matched)
)

print(
    "Missing:",
    len(missing)
)

print(
    "Extra:",
    len(extra)
)

print(
    "Coverage:",
    f"{coverage * 100:.2f}%"
)


# ==========================================
# Missing samples
# ==========================================

if missing:

    print("")
    print("Missing sample:")

    for code in sorted(
        missing
    )[:30]:

        print(
            " -",
            code
        )


# ==========================================
# Gate
# ==========================================

print("")

if coverage < MIN_COVERAGE:

    print("==============================")
    print("COVERAGE GATE: FAILED")
    print("==============================")

    print(
        f"{coverage * 100:.2f}% "
        f"< {MIN_COVERAGE * 100:.0f}%"
    )

    sys.exit(2)


print("==============================")
print("COVERAGE GATE: PASS")
print("==============================")
