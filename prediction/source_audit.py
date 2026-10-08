def run_source_audit(
    market_data,
    prediction_cutoff,
):

    sources = market_data.get(
        "sources",
        []
    )

    if not sources:
        return {
            "status": "FAILED",
            "reason": "No auditable sources",
        }

    return {
        "status": "PASS",
        "sources": sources,
    }
