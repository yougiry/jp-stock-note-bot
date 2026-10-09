import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from collect import collect_market_data
from source_audit import run_source_audit
from scoring import run_scoring
from freeze import create_freeze


JST = ZoneInfo("Asia/Tokyo")

OUTPUT_DIR = Path("data/prediction")

PREDICTION_CUTOFF_HOUR = 6
PREDICTION_CUTOFF_MINUTE = 0


def fail(message):
    print("")
    print("==============================")
    print("v5.11: NO-RUN")
    print(message)
    print("==============================")
    sys.exit(1)


def get_prediction_cutoff(now):
    """
    Return the official Prediction Cutoff.

    v5.11 morning prediction is frozen at 06:00 JST.

    If execution occurs before 06:00 JST, the run must stop.
    Information obtained after 06:00 JST must never flow back
    into the Prediction.
    """

    cutoff = datetime.combine(
        now.date(),
        time(
            PREDICTION_CUTOFF_HOUR,
            PREDICTION_CUTOFF_MINUTE,
        ),
        tzinfo=JST,
    )

    if now < cutoff:
        fail(
            "Execution occurred before the "
            "06:00 JST Prediction Cutoff"
        )

    return cutoff


def get_next_weekday(base_date):
    """
    Return the next weekday after base_date.

    IMPORTANT:
    This is only a temporary business-day resolver.

    It excludes Saturday and Sunday but does not yet
    exclude Japanese market holidays or special JPX
    non-trading days.

    A proper JPX trading calendar will replace this
    function in the next implementation step.
    """

    candidate = base_date + timedelta(days=1)

    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)

    return candidate


def main():

    execution_time = datetime.now(JST)

    prediction_cutoff = get_prediction_cutoff(
        execution_time
    )

    target_day = get_next_weekday(
        prediction_cutoff.date()
    )

    target_date = target_day.strftime("%Y%m%d")

    print("")
    print("==============================")
    print("Prediction Engine v5.11")
    print("==============================")

    print(
        "Execution time:",
        execution_time.isoformat(),
    )

    print(
        "Prediction cutoff:",
        prediction_cutoff.isoformat(),
    )

    print(
        "Target date:",
        target_date,
    )

    print(
        "Calendar status:",
        "WEEKDAY_ONLY",
    )

    # ------------------------------------------
    # STEP 1
    # Market / Web data collection
    # ------------------------------------------

    print("")
    print("[1/4] MARKET DATA COLLECTION")

    market_data = collect_market_data(
        target_date=target_date,
        execution_time=execution_time,
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
        prediction_cutoff=prediction_cutoff,
    )

    if not audit:
        fail(
            "Source Audit returned no result"
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
        prediction_cutoff=prediction_cutoff,
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
        prediction_cutoff=prediction_cutoff,
    )

    if not frozen:
        fail(
            "Freeze generation failed"
        )

    # ------------------------------------------
    # Prediction metadata
    # ------------------------------------------

    frozen["target_date"] = target_date
    frozen["execution_time"] = (
        execution_time.isoformat()
    )
    frozen["prediction_cutoff"] = (
        prediction_cutoff.isoformat()
    )

    frozen["calendar_status"] = (
        "WEEKDAY_ONLY"
    )

    frozen["prediction_status"] = (
        "FROZEN"
    )

    # ------------------------------------------
    # Save
    # ------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        OUTPUT_DIR
        / f"v511_{target_date}.json"
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
        frozen.get("prediction_id"),
    )

    print(
        "Prediction cutoff:",
        frozen.get("prediction_cutoff"),
    )

    print(
        "Target date:",
        frozen.get("target_date"),
    )

    print(
        "Calendar status:",
        frozen.get("calendar_status"),
    )

    print(
        "Coverage:",
        frozen.get("coverage"),
    )

    print(
        "Candidates:",
        len(
            frozen.get(
                "candidates",
                []
            )
        ),
    )

    print(
        "Output:",
        output,
    )


if __name__ == "__main__":
    main()
