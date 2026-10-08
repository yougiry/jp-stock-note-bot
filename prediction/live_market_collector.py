"""
LIVE Market Collector
Prediction Engine v5.11

Critical principles:
- Prediction and Validation must remain separated.
- No future information may enter Prediction.
- Missing data must never be estimated.
- Stale market data must never be treated as LIVE.
- Coverage must be measured against the supplied JPX universe.
- Source permission must be explicitly confirmed.
- prediction_eligible becomes True only after all critical gates pass.
"""

from collections import Counter
from datetime import date, datetime


MIN_COVERAGE = 0.90


class LiveMarketDataError(RuntimeError):
    pass


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def _as_datetime(value):
    if isinstance(value, datetime):
        return value

    if not value:
        raise LiveMarketDataError(
            "Timestamp is missing"
        )

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise LiveMarketDataError(
            f"Invalid timestamp: {value}"
        ) from exc


def _compare_timestamps(left, right):
    """
    Compare two timestamps safely.

    Mixing timezone-aware and timezone-naive
    timestamps is rejected.
    """

    left_dt = _as_datetime(left)
    right_dt = _as_datetime(right)

    left_aware = (
        left_dt.utcoffset() is not None
    )

    right_aware = (
        right_dt.utcoffset() is not None
    )

    if left_aware != right_aware:
        raise LiveMarketDataError(
            "Timestamp timezone mismatch"
        )

    return left_dt, right_dt


def validate_live_market(
    bars,
    universe_codes,
    expected_trading_date,
    source_name,
    retrieved_at,
    prediction_cutoff,
    automated_access_allowed,
    commercial_use_allowed,
):
    """
    Validate a normalized LIVE market dataset.

    A dataset is Prediction-eligible only when
    every critical gate passes.

    publication_at is evaluated per record.

    If publication_at is missing, that record
    cannot enter Prediction.
    """

    critical_gate = {
        "source_identity": False,
        "automated_access": False,
        "commercial_use": False,
        "retrieval_before_cutoff": False,
        "publication_before_cutoff": False,
        "freshness": False,
        "ohlcv_integrity": False,
        "coverage": False,
    }

    # -------------------------------------------------
    # Gate 1: source identity
    # -------------------------------------------------

    if not source_name:
        raise LiveMarketDataError(
            "source_name is required"
        )

    critical_gate["source_identity"] = True

    # -------------------------------------------------
    # Gate 2: permission
    # -------------------------------------------------

    if automated_access_allowed is not True:
        raise LiveMarketDataError(
            "Automated access permission "
            "is not confirmed"
        )

    critical_gate["automated_access"] = True

    if commercial_use_allowed is not True:
        raise LiveMarketDataError(
            "Commercial use permission "
            "is not confirmed"
        )

    critical_gate["commercial_use"] = True

    # -------------------------------------------------
    # Gate 3: timestamps
    # -------------------------------------------------

    retrieval_dt, cutoff_dt = _compare_timestamps(
        retrieved_at,
        prediction_cutoff,
    )

    if retrieval_dt > cutoff_dt:
        raise LiveMarketDataError(
            "Market data was retrieved after "
            "Prediction Cutoff"
        )

    critical_gate[
        "retrieval_before_cutoff"
    ] = True

    expected_date = _as_date(
        expected_trading_date
    ).isoformat()

    # -------------------------------------------------
    # Universe
    # -------------------------------------------------

    universe = {
        str(code).strip()
        for code in universe_codes
        if str(code).strip()
    }

    if not universe:
        raise LiveMarketDataError(
            "JPX universe is empty"
        )

    # -------------------------------------------------
    # Record validation
    # -------------------------------------------------

    valid_by_code = {}

    stale = []
    malformed = []
    future_publication = []
    missing_publication = []

    seen = Counter()

    for bar in bars:

        if not isinstance(bar, dict):
            malformed.append("UNKNOWN")
            continue

        try:
            code = str(
                bar["code"]
            ).strip()

            trading_date = str(
                bar["date"]
            )

            seen[code] += 1

            if code not in universe:
                continue

            # -----------------------------
            # Freshness
            # -----------------------------

            if trading_date != expected_date:
                stale.append(
                    {
                        "code": code,
                        "date": trading_date,
                    }
                )
                continue

            # -----------------------------
            # OHLCV
            # -----------------------------

            required = (
                "open",
                "high",
                "low",
                "close",
                "volume",
            )

            if any(
                bar.get(field) is None
                for field in required
            ):
                malformed.append(code)
                continue

            opening = float(
                bar["open"]
            )

            high = float(
                bar["high"]
            )

            low = float(
                bar["low"]
            )

            close = float(
                bar["close"]
            )

            volume = float(
                bar["volume"]
            )

            if min(
                opening,
                high,
                low,
                close,
            ) <= 0:
                malformed.append(code)
                continue

            if volume < 0:
                malformed.append(code)
                continue

            if high < max(
                opening,
                close,
                low,
            ):
                malformed.append(code)
                continue

            if low > min(
                opening,
                close,
                high,
            ):
                malformed.append(code)
                continue

            # -----------------------------
            # Publication timestamp
            # -----------------------------

            publication_at = bar.get(
                "publication_at"
            )

            if not publication_at:
                missing_publication.append(
                    code
                )
                continue

            publication_dt, row_cutoff_dt = (
                _compare_timestamps(
                    publication_at,
                    prediction_cutoff,
                )
            )

            if publication_dt > row_cutoff_dt:
                future_publication.append(
                    code
                )
                continue

            valid_by_code[code] = bar

        except (
            KeyError,
            TypeError,
            ValueError,
            LiveMarketDataError,
        ):
            malformed.append(
                str(
                    bar.get(
                        "code",
                        "UNKNOWN",
                    )
                )
            )

    # -------------------------------------------------
    # Duplicate audit
    # -------------------------------------------------

    duplicate_codes = sorted(
        code
        for code, count in seen.items()
        if count > 1
    )

    # -------------------------------------------------
    # Coverage
    # -------------------------------------------------

    universe_count = len(
        universe
    )

    matched_count = len(
        valid_by_code
    )

    coverage = (
        matched_count / universe_count
        if universe_count
        else 0.0
    )

    missing_codes = sorted(
        universe - set(valid_by_code)
    )

    critical_gate["freshness"] = (
        len(stale) == 0
    )

    critical_gate["ohlcv_integrity"] = (
        len(malformed) == 0
    )

    critical_gate[
        "publication_before_cutoff"
    ] = (
        len(missing_publication) == 0
        and
        len(future_publication) == 0
    )

    critical_gate["coverage"] = (
        coverage >= MIN_COVERAGE
    )

    # -------------------------------------------------
    # Final Critical Gate
    # -------------------------------------------------

    critical_gate_pass = all(
        critical_gate.values()
    )

    audit = {
        "source": source_name,

        "expected_trading_date":
            expected_date,

        "retrieved_at":
            retrieved_at,

        "prediction_cutoff":
            prediction_cutoff,

        "universe_count":
            universe_count,

        "matched_count":
            matched_count,

        "coverage":
            round(
                coverage,
                6,
            ),

        "minimum_coverage":
            MIN_COVERAGE,

        "missing_count":
            len(missing_codes),

        "stale_count":
            len(stale),

        "malformed_count":
            len(malformed),

        "duplicate_count":
            len(duplicate_codes),

        "missing_publication_count":
            len(missing_publication),

        "future_publication_count":
            len(future_publication),

        "critical_gate":
            critical_gate,

        "status": (
            "PASS"
            if critical_gate_pass
            else "FAIL"
        ),
    }

    if not critical_gate_pass:
        failed = [
            name
            for name, passed
            in critical_gate.items()
            if not passed
        ]

        raise LiveMarketDataError(
            "LIVE Critical Gate failed: "
            + ", ".join(failed)
            + " | coverage="
            + f"{matched_count}/"
            + f"{universe_count} "
            + f"({coverage:.2%})"
        )

    # -------------------------------------------------
    # Prediction eligibility
    # -------------------------------------------------

    approved = []

    for code in sorted(
        valid_by_code
    ):
        item = dict(
            valid_by_code[code]
        )

        item[
            "prediction_eligible"
        ] = True

        approved.append(item)

    return {
        "bars": approved,
        "audit": audit,
        "missing_codes":
            missing_codes,
        "stale_rows":
            stale,
        "malformed_codes":
            sorted(
                set(malformed)
            ),
        "duplicate_codes":
            duplicate_codes,
        "missing_publication_codes":
            sorted(
                set(
                    missing_publication
                )
            ),
        "future_publication_codes":
            sorted(
                set(
                    future_publication
                )
            ),
    }
