from datetime import date, timedelta


# --------------------------------------------------
# JPX non-trading dates
# --------------------------------------------------
#
# v5.11 Prediction Engine
#
# This list contains explicitly verified JPX
# non-trading weekdays.
#
# Do NOT infer unknown holidays.
# Do NOT silently treat every Japanese public
# holiday as a JPX holiday.
#
# Add future years only after their JPX calendar
# has been verified.
# --------------------------------------------------


JPX_NON_TRADING_DATES = {

    # 2026

    date(2026, 1, 1),
    date(2026, 1, 2),
    date(2026, 1, 12),
    date(2026, 2, 11),
    date(2026, 2, 23),
    date(2026, 3, 20),
    date(2026, 4, 29),
    date(2026, 5, 4),
    date(2026, 5, 5),
    date(2026, 5, 6),
    date(2026, 7, 20),
    date(2026, 8, 11),
    date(2026, 9, 21),
    date(2026, 9, 22),
    date(2026, 9, 23),
    date(2026, 10, 12),
    date(2026, 11, 3),
    date(2026, 11, 23),
    date(2026, 12, 31),
}


SUPPORTED_YEARS = {
    2026,
}


def is_weekend(day):
    """
    Saturday = 5
    Sunday   = 6
    """

    return day.weekday() >= 5


def is_supported_year(day):
    """
    Return True only when the calendar for the
    requested year has been explicitly registered.
    """

    return day.year in SUPPORTED_YEARS


def is_trading_day(day):
    """
    Determine whether a date is a JPX trading day.

    Returns:
        True  -> trading day
        False -> weekend / registered JPX non-trading day

    Raises:
        ValueError when the calendar year has not
        been explicitly registered.

    This prevents v5.11 from silently predicting
    against an unverified future calendar.
    """

    if not isinstance(day, date):
        raise TypeError(
            "day must be datetime.date"
        )

    if not is_supported_year(day):
        raise ValueError(
            "JPX calendar is not registered "
            f"for year {day.year}"
        )

    if is_weekend(day):
        return False

    if day in JPX_NON_TRADING_DATES:
        return False

    return True


def get_next_trading_day(day):
    """
    Return the first registered JPX trading day
    strictly after `day`.
    """

    if not isinstance(day, date):
        raise TypeError(
            "day must be datetime.date"
        )

    candidate = day + timedelta(days=1)

    # Safety guard against accidental infinite loops.
    for _ in range(14):

        if not is_supported_year(candidate):
            raise ValueError(
                "JPX calendar is not registered "
                f"for year {candidate.year}"
            )

        if is_trading_day(candidate):
            return candidate

        candidate += timedelta(days=1)

    raise RuntimeError(
        "Unable to resolve next JPX trading day "
        "within 14 calendar days"
    )


def get_previous_trading_day(day):
    """
    Return the first registered JPX trading day
    strictly before `day`.
    """

    if not isinstance(day, date):
        raise TypeError(
            "day must be datetime.date"
        )

    candidate = day - timedelta(days=1)

    for _ in range(14):

        if not is_supported_year(candidate):
            raise ValueError(
                "JPX calendar is not registered "
                f"for year {candidate.year}"
            )

        if is_trading_day(candidate):
            return candidate

        candidate -= timedelta(days=1)

    raise RuntimeError(
        "Unable to resolve previous JPX trading day "
        "within 14 calendar days"
    )
