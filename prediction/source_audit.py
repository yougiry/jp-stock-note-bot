from datetime import datetime


def run_source_audit(market_data, prediction_cutoff):
    sources = market_data.get("sources", [])
    if not sources:
        return {"status": "FAILED", "reason": "No auditable sources"}

    checked = []
    for source in sources:
        row = dict(source)
        row["cutoff_relation"] = "UNKNOWN"
        ts = row.get("retrieval_timestamp")
        if ts:
            try:
                retrieved = datetime.fromisoformat(ts)
                row["cutoff_relation"] = (
                    "AT_OR_BEFORE_CUTOFF" if retrieved <= prediction_cutoff
                    else "AFTER_CUTOFF_RETRIEVAL"
                )
            except ValueError:
                return {"status": "FAILED", "reason": f"Invalid timestamp: {ts}"}
        checked.append(row)

    return {"status": "PASS", "sources": checked}
