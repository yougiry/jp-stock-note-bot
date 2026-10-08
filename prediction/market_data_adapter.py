"""Market data normalization for Prediction Engine v5.11."""

from datetime import date, datetime
from math import isfinite


class MarketDataError(ValueError):
    pass


def normalize_code(value):
    code = str(value).strip().upper()

    if code.endswith(".T"):
        code = code[:-2]

    if code.endswith(".JP"):
        code = code[:-3]

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5 and code.endswith("0"):
        code = code[:4]

    if len(code) != 4 or not code.isalnum():
        raise MarketDataError(
            f"Invalid security code: {value}"
        )

    return code


def normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return date.fromisoformat(str(value)).isoformat()


def numeric(value, field, required=True):
    if value is None or value == "":
        if required:
            raise MarketDataError(
                f"Missing required field: {field}"
            )
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise MarketDataError(
            f"Invalid numeric field: {field}"
        )

    if not isfinite(number):
        raise MarketDataError(
            f"Non-finite numeric field: {field}"
        )

    return number


def normalize_bar(row, source, retrieved_at):
    """
    Convert external daily OHLCV data
    into the internal v5.11 schema.

    No missing values are estimated.
    """

    if not source:
        raise MarketDataError("Source is required")

    if not retrieved_at:
        raise MarketDataError(
            "Retrieval timestamp is required"
        )

    code = normalize_code(
        row.get("code") or row.get("ticker")
    )

    trading_date = normalize_date(
        row.get("date")
    )

    opening = numeric(
        row.get("open"), "open"
    )
    high = numeric(
        row.get("high"), "high"
    )
    low = numeric(
        row.get("low"), "low"
    )
    close = numeric(
        row.get("close"), "close"
    )
    volume = numeric(
        row.get("volume"), "volume"
    )

    turnover = numeric(
        row.get("turnover"),
        "turnover",
        required=False,
    )

    if min(opening, high, low, close) <= 0:
        raise MarketDataError(
            "OHLC prices must be positive"
        )

    if volume < 0:
        raise MarketDataError(
            "Volume cannot be negative"
        )

    if turnover is not None and turnover < 0:
        raise MarketDataError(
            "Turnover cannot be negative"
        )

    if high < max(opening, close, low):
        raise MarketDataError(
            "Invalid high price"
        )

    if low > min(opening, close, high):
        raise MarketDataError(
            "Invalid low price"
        )

    return {
        "code": code,
        "date": trading_date,
        "open": opening,
        "high": high,
        "low": low,
        "close": close,
        "volume": int(volume),
        "turnover": turnover,
        "source": source,
        "retrieved_at": retrieved_at,
        "publication_at": row.get(
            "publication_at"
        ),
        "prediction_eligible": False,
    }
