import json
import os
import sys
from pathlib import Path
from datetime import datetime


INPUT = Path(
    os.environ.get(
        "PREDICTION_JSON",
        ""
    )
)

MIN_COVERAGE = 0.90


def fail(message):
    print("")
    print("==============================")
    print("FREEZE VALIDATION: FAILED")
    print(message)
    print("==============================")
    sys.exit(1)


if not str(INPUT):
    fail("PREDICTION_JSON is not specified")

if not INPUT.exists():
    fail(f"Prediction JSON not found: {INPUT}")


with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)


# ==========================================
# Required top-level fields
# ==========================================

required = [
    "prediction_id",
    "cutoff",
    "freeze_time",
    "status",
    "source_audit",
    "critical_gate",
    "freeze_status",
    "coverage",
    "candidates",
]

for field in required:
    if field not in data:
        fail(f"Missing required field: {field}")


# ==========================================
# Formal v5.11 Gates
# ==========================================

if data["status"] != "VALID":
    fail("status != VALID")

if data["source_audit"] != "PASS":
    fail("source_audit != PASS")

if data["critical_gate"] != "PASS":
    fail("critical_gate != PASS")

if data["freeze_status"] != "PASS":
    fail("freeze_status != PASS")


try:
    coverage = float(data["coverage"])
except (TypeError, ValueError):
    fail("coverage is invalid")

if coverage < MIN_COVERAGE:
    fail(
        f"coverage {coverage:.3f} "
        f"is below {MIN_COVERAGE:.2f}"
    )


# ==========================================
# Timestamp validation
# ==========================================

try:
    cutoff = datetime.fromisoformat(
        data["cutoff"]
    )

    freeze_time = datetime.fromisoformat(
        data["freeze_time"]
    )

except Exception:
    fail("Invalid cutoff/freeze_time format")


if freeze_time < cutoff:
    fail("freeze_time is earlier than cutoff")


# ==========================================
# Prediction ID
# ==========================================

prediction_id = str(
    data["prediction_id"]
).strip()

if not prediction_id:
    fail("prediction_id is empty")


# ==========================================
# Candidates
# ==========================================

candidates = data["candidates"]

if not isinstance(candidates, list):
    fail("candidates is not a list")


required_candidate_fields = [
    "rank",
    "code",
    "name",
    "decision",
    "previous_close",
    "unit",
    "required_capital",
    "surge_score",
    "limit_up_score",
    "entry_score",
    "risk",
    "reason",
]


seen_ranks = set()
seen_codes = set()


for index, candidate in enumerate(
    candidates,
    start=1
):

    if not isinstance(candidate, dict):
        fail(
            f"candidate #{index} "
            "is not an object"
        )

    for field in required_candidate_fields:

        if field not in candidate:
            fail(
                f"candidate #{index}: "
                f"missing {field}"
            )

    rank = candidate["rank"]
    code = str(candidate["code"]).strip()

    if rank in seen_ranks:
        fail(
            f"duplicate rank: {rank}"
        )

    if code in seen_codes:
        fail(
            f"duplicate code: {code}"
        )

    seen_ranks.add(rank)
    seen_codes.add(code)


# ==========================================
# Result
# ==========================================

print("")
print("==============================")
print("v5.11 FREEZE VALIDATION: PASS")
print("==============================")

print("Prediction ID:", prediction_id)
print("Cutoff:", data["cutoff"])
print("Freeze time:", data["freeze_time"])
print("Coverage:", f"{coverage * 100:.1f}%")
print("Candidates:", len(candidates))
print("Input:", INPUT)
