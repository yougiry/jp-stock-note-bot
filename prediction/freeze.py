from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
MIN_COVERAGE = 0.90


def create_freeze(result, audit, prediction_cutoff):
    if not result or audit.get("status") != "PASS":
        return None

    coverage = float(result.get("coverage", 0) or 0)
    if coverage < MIN_COVERAGE:
        return None

    candidates = result.get("candidates", [])
    if not isinstance(candidates, list):
        return None

    freeze_time = datetime.now(JST)
    seed = f"{prediction_cutoff.isoformat()}|{result.get('score_version')}|{len(candidates)}"
    digest = sha256(seed.encode("utf-8")).hexdigest()[:10].upper()
    prediction_id = f"JP-{prediction_cutoff:%Y%m%d}-V511-{digest}"

    normalized = []
    for item in candidates:
        row = dict(item)
        row.setdefault("unit", 100)
        normalized.append(row)

    return {
        "prediction_id": prediction_id,
        "cutoff": prediction_cutoff.isoformat(),
        "freeze_time": freeze_time.isoformat(),
        "status": "VALID",
        "source_audit": "PASS",
        "source_audit_ledger": audit.get("sources", []),
        "critical_gate": "PASS",
        "freeze_status": "PASS",
        "coverage": coverage,
        "score_version": result.get("score_version"),
        "ranking_type": result.get("ranking_type"),
        "formal_prediction": result.get("formal_prediction", False),
        "candidates": normalized,
    }
