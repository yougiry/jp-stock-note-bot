from datetime import date, datetime, time
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")


def _parse_timestamp(value):
    """
    Parse an ISO timestamp.

    Returns:
        datetime
        None

    Date-only values are intentionally not converted
    to midnight here because a publication date alone
    does not prove publication before the Prediction
    Cutoff.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value

    elif isinstance(value, date):
        return None

    elif isinstance(value, str):

        text = value.strip()

        if not text:
            return None

        # YYYY-MM-DD is only a date.
        # It does not prove publication time.
        try:
            if len(text) == 10:
                date.fromisoformat(text)
                return None
        except ValueError:
            pass

        try:
            parsed = datetime.fromisoformat(
                text.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError:
            return None

    else:
        return None

    # A naive datetime has no trustworthy timezone.
    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(JST)


def _normalize_cutoff(prediction_cutoff):
    """
    Require an explicit timezone-aware cutoff.
    """

    if not isinstance(
        prediction_cutoff,
        datetime,
    ):
        raise TypeError(
            "prediction_cutoff must be datetime"
        )

    if prediction_cutoff.tzinfo is None:
        raise ValueError(
            "prediction_cutoff must be timezone-aware"
        )

    return prediction_cutoff.astimezone(JST)


def run_source_audit(
    market_data,
    prediction_cutoff,
):
    """
    Audit all sources before v5.11 scoring.

    Important distinction:

    publication_timestamp
        Determines whether information was publicly
        available by the Prediction Cutoff.

    retrieval_timestamp
        Records when the engine actually retrieved
        the information.

    Retrieval after the cutoff does NOT by itself
    prove future leakage.

    However, a source cannot participate in scoring
    unless its publication time is proven to be at
    or before the cutoff.
    """

    try:
        cutoff = _normalize_cutoff(
            prediction_cutoff
        )

    except (TypeError, ValueError) as exc:
        return {
            "status": "FAILED",
            "reason": str(exc),
            "sources": [],
        }

    sources = market_data.get(
        "sources",
        [],
    )

    if not sources:
        return {
            "status": "FAILED",
            "reason": "No auditable sources",
            "sources": [],
        }

    checked = []

    eligible_count = 0
    blocked_count = 0

    for source in sources:

        row = dict(source)

        requested_scoring = bool(
            row.get(
                "scoring_eligible",
                False,
            )
        )

        # --------------------------------------
        # Retrieval timestamp audit
        # --------------------------------------

        retrieval_raw = row.get(
            "retrieval_timestamp"
        )

        retrieved = _parse_timestamp(
            retrieval_raw
        )

        if retrieval_raw is None:
            row["retrieval_relation"] = (
                "UNKNOWN"
            )

        elif retrieved is None:
            row["retrieval_relation"] = (
                "INVALID_OR_UNVERIFIED"
            )

        elif retrieved <= cutoff:
            row["retrieval_relation"] = (
                "AT_OR_BEFORE_CUTOFF"
            )

        else:
            row["retrieval_relation"] = (
                "AFTER_CUTOFF"
            )

        # Keep compatibility with the previous
        # ledger field name.
        row["cutoff_relation"] = (
            row["retrieval_relation"]
        )

        # --------------------------------------
        # Publication timestamp audit
        # --------------------------------------

        publication_raw = row.get(
            "publication_timestamp"
        )

        published = _parse_timestamp(
            publication_raw
        )

        if publication_raw is None:

            publication_relation = (
                "UNKNOWN"
            )

        elif published is None:

            publication_relation = (
                "UNVERIFIED_TIME"
            )

        elif published <= cutoff:

            publication_relation = (
                "AT_OR_BEFORE_CUTOFF"
            )

        else:

            publication_relation = (
                "AFTER_CUTOFF"
            )

        row["publication_relation"] = (
            publication_relation
        )

        # --------------------------------------
        # Final scoring eligibility
        # --------------------------------------

        audit_reasons = []

        if not requested_scoring:
            audit_reasons.append(
                row.get(
                    "exclusion_reason"
                )
                or
                "Source not requested for scoring"
            )

        if publication_relation == "UNKNOWN":
            audit_reasons.append(
                "Publication timestamp missing"
            )

        elif publication_relation == (
            "UNVERIFIED_TIME"
        ):
            audit_reasons.append(
                "Publication time cannot be "
                "verified against cutoff"
            )

        elif publication_relation == (
            "AFTER_CUTOFF"
        ):
            audit_reasons.append(
                "Published after Prediction Cutoff"
            )

        # Retrieval timestamps are audit evidence,
        # but retrieval after 06:00 is not by itself
        # future leakage.
        #
        # An invalid supplied retrieval timestamp is
        # nevertheless a ledger integrity problem.

        if (
            retrieval_raw is not None
            and retrieved is None
        ):
            audit_reasons.append(
                "Invalid or timezone-unverified "
                "retrieval timestamp"
            )

        final_scoring_eligible = (
            requested_scoring
            and publication_relation
            == "AT_OR_BEFORE_CUTOFF"
            and not (
                retrieval_raw is not None
                and retrieved is None
            )
        )

        row[
            "requested_scoring_eligible"
        ] = requested_scoring

        row[
            "scoring_eligible"
        ] = final_scoring_eligible

        row["audit_reasons"] = (
            audit_reasons
        )

        row["audit_status"] = (
            "ELIGIBLE"
            if final_scoring_eligible
            else "BLOCKED"
        )

        if final_scoring_eligible:
            eligible_count += 1
        else:
            blocked_count += 1

        checked.append(row)

    # ------------------------------------------
    # Overall audit
    # ------------------------------------------
    #
    # Zero scoring sources is NOT a Source Audit
    # failure.
    #
    # It means the engine currently has no
    # cutoff-safe source for those factors.
    #
    # Scoring must treat those factors as NA
    # rather than inventing values.
    # ------------------------------------------

    return {
        "status": "PASS",
        "prediction_cutoff": (
            cutoff.isoformat()
        ),
        "sources": checked,
        "eligible_source_count": (
            eligible_count
        ),
        "blocked_source_count": (
            blocked_count
        ),
        "scoring_data_status": (
            "AVAILABLE"
            if eligible_count > 0
            else "NA"
        ),
    }
