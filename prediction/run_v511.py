import json
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from collect import collect_market_data
from source_audit import run_source_audit
from scoring import run_scoring
from freeze import create_freeze
from trading_calendar import get_next_trading_day


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
    Return the official v5.11 Prediction Cutoff.

    Morning Prediction is frozen at 06:00 JST.

    Execution before 06:00 JST is not permitted.

    Execution after 06:00 JST does not move the cutoff.
    Information published or obtained after the cutoff
    must not flow back into Prediction scoring.
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


def main():

    execution_time = datetime.now(JST)

    prediction_cutoff = get_prediction_cutoff(
        execution_time
    )

    # ------------------------------------------
    # Resolve next JPX trading day
    # ------------------------------------------

    try:
        target_day = get_next_trading_day(
            prediction_cutoff.date()
        )

    except (ValueError, TypeError, RuntimeError) as exc:
        fail(
            "Unable to resolve JPX trading day: "
            f"{exc}"
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
        "JPX_VERIFIED",
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
    # Prediction Freeze
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
        "JPX_VERIFIED"
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
