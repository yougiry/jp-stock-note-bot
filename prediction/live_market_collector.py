"""
LIVE Market Collector
Prediction Engine v5.11

Responsibilities:
- receive normalized OHLCV bars
- validate freshness
- validate JPX universe coverage
- reject incomplete LIVE datasets
- produce Source Audit metadata

This module does NOT estimate missing market data.
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


def validate_live_market(
    bars,
    universe_codes,
    expected_trading_date,
    source_name,
    retrieved_at,
):
    """
    Validate a normalized LIVE market dataset.

    bars:
        output compatible with market_data_adapter.normalize_bar()

    universe_codes:
        JPX universe security codes

    expected_trading_date:
        trading date required for this Prediction run
    """

    if not source_name:
        raise LiveMarketDataError(
            "source_name is required"
        )

    if not retrieved_at:
        raise LiveMarketDataError(
            "retrieved_at is required"
        )

    expected_date = _as_date(
        expected_trading_date
    ).isoformat()

    universe = {
        str(code).strip()
        for code in universe_codes
        if str(code).strip()
    }

    if not universe:
        raise LiveMarketDataError(
            "JPX universe is empty"
        )

    valid_by_code = {}
    stale = []
    malformed = []
    duplicate_codes = []

    seen = Counter()

    for bar in bars:
        try:
            code = str(bar["code"]).strip()
            trading_date = str(bar["date"])

            seen[code] += 1

            if trading_date != expected_date:
                stale.append(
                    {
                        "code": code,
                        "date": trading_date,
                    }
                )
                continue

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

            if code not in universe:
                continue

            valid_by_code[code] = bar

        except (KeyError, TypeError, ValueError):
            malformed.append(
                str(bar.get("code", "UNKNOWN"))
                if isinstance(bar, dict)
                else "UNKNOWN"
            )

    duplicate_codes = sorted(
        code
        for code, count in seen.items()
        if count > 1
    )

    universe_count = len(universe)
    matched_count = len(valid_by_code)

    coverage = (
        matched_count / universe_count
        if universe_count
        else 0.0
    )

    missing_codes = sorted(
        universe - set(valid_by_code)
    )

    passed = coverage >= MIN_COVERAGE

    audit = {
        "source": source_name,
        "expected_trading_date": expected_date,
        "retrieved_at": retrieved_at,

        "universe_count": universe_count,
        "matched_count": matched_count,

        "coverage": round(
            coverage,
            6,
        ),

        "minimum_coverage": MIN_COVERAGE,

        "missing_count": len(
            missing_codes
        ),

        "stale_count": len(stale),

        "malformed_count": len(
            malformed
        ),

        "duplicate_count": len(
            duplicate_codes
        ),

        "status": (
            "PASS"
            if passed
            else "FAIL"
        ),
    }

    if not passed:
        raise LiveMarketDataError(
            "LIVE market coverage gate failed: "
            f"{matched_count}/{universe_count} "
            f"({coverage:.2%})"
        )

    approved = []

    for code in sorted(valid_by_code):
        item = dict(
            valid_by_code[code]
        )

        item["prediction_eligible"] = True

        approved.append(item)

    return {
        "bars": approved,
        "audit": audit,
        "missing_codes": missing_codes,
        "stale_rows": stale,
        "malformed_codes": sorted(
            set(malformed)
        ),
        "duplicate_codes": duplicate_codes,
    }
