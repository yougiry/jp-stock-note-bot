import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from collect import collect_market_data
from source_audit import run_source_audit
from scoring import run_scoring
from freeze import create_freeze


JST = ZoneInfo("Asia/Tokyo")

OUTPUT_DIR = Path("data/prediction")


def fail(message):
    print("")
    print("==============================")
    print("v5.11: NO-RUN")
    print(message)
    print("==============================")
    sys.exit(1)


def main():

    now = datetime.now(JST)
    target_date = now.strftime("%Y%m%d")

    print("")
    print("==============================")
    print("Prediction Engine v5.11")
    print("==============================")

    print(
        "Execution time:",
        now.isoformat()
    )

    print(
        "Target date:",
        target_date
    )

    # ------------------------------------------
    # STEP 1
    # Market data collection
    # ------------------------------------------

    print("")
    print("[1/4] MARKET DATA COLLECTION")

    market_data = collect_market_data(
        target_date=target_date,
        execution_time=now,
    )

    if not market_data:
        fail(
            "Market data collection returned "
            "no usable dataset"
        )

    # ------------------------------------------
    # STEP 2
    # Source Audit
    # ------------------------------------------

    print("")
    print("[2/4] SOURCE AUDIT")

    audit = run_source_audit(
        market_data=market_data,
        prediction_cutoff=now,
    )

    if audit.get("status") != "PASS":
        fail(
            "Source Audit failed"
        )

    # ------------------------------------------
    # STEP 3
    # v5.11 scoring
    # ------------------------------------------

    print("")
    print("[3/4] v5.11 SCORING")

    result = run_scoring(
        market_data=market_data,
        audit=audit,
        prediction_cutoff=now,
    )

    if not result:
        fail(
            "Scoring returned no result"
        )

    # ------------------------------------------
    # STEP 4
    # Freeze
    # ------------------------------------------

    print("")
    print("[4/4] PREDICTION FREEZE")

    frozen = create_freeze(
        result=result,
        audit=audit,
        prediction_cutoff=now,
    )

    if not frozen:
        fail(
            "Freeze generation failed"
        )

    frozen["target_date"] = target_date

    # ------------------------------------------
    # Save
    # ------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output = (
        OUTPUT_DIR /
        f"v511_{target_date}.json"
    )

    if output.exists():
        fail(
            f"Prediction already exists: {output}"
        )

    output.write_text(
        json.dumps(
            frozen,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("==============================")
    print("v5.11 FREEZE: SUCCESS")
    print("==============================")

    print(
        "Prediction ID:",
        frozen.get("prediction_id")
    )

    print(
        "Coverage:",
        frozen.get("coverage")
    )

    print(
        "Candidates:",
        len(
            frozen.get(
                "candidates",
                []
            )
        )
    )

    print(
        "Output:",
        output
    )


if __name__ == "__main__":
    main()
