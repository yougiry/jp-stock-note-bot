def run_scoring(
    market_data,
    audit,
    prediction_cutoff,
):

    stocks = market_data.get(
        "stocks",
        []
    )

    if not stocks:
        return None

    # Actual v5.11 seven-factor scoring
    # will be implemented after collectors
    # are connected.

    return None
