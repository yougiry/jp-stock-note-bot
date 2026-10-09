"""
Market Source Registry
Prediction Engine v5.11

Tracks candidate data sources.

IMPORTANT:
- Candidate status does not imply permission.
- Unknown permissions must remain False.
- No source is approved for LIVE Prediction yet.
"""

SOURCES = {
    "JPX_QUOTE": {
        "name": "JPX Stock Quote",
        "type": "WEB",
        "url": (
            "https://quote.jpx.co.jp/"
            "jpxhp/main/index.aspx?F=stock_search"
        ),
        "ohlcv": True,
        "freshness": "DELAYED_15_MIN_OR_MORE",
        "automated_access_allowed": False,
        "commercial_use_allowed": False,
        "permission_verified": False,
        "coverage_verified": False,
        "status": "RESEARCH",
    },
    "JPX_DAILY_REPORT": {
        "name": "JPX Daily Report",
        "type": "OFFICIAL_REPORT",
        "url": (
            "https://www.jpx.co.jp/"
            "markets/statistics-equities/daily/01.html"
        ),
        "ohlcv": True,
        "freshness": "NEXT_BUSINESS_DAY",
        "automated_access_allowed": False,
        "commercial_use_allowed": False,
        "permission_verified": False,
        "coverage_verified": False,
        "status": "RESEARCH",
    },
    "STOOQ": {
        "name": "Stooq",
        "type": "CSV",
        "url": "https://stooq.com/",
        "ohlcv": False,
        "freshness": "UNKNOWN",
        "automated_access_allowed": False,
        "commercial_use_allowed": False,
        "permission_verified": False,
        "coverage_verified": False,
        "status": "FAILED_INITIAL_TEST",
    },
}


def get_source(name):
    if name not in SOURCES:
        raise KeyError(
            f"Unknown market source: {name}"
        )

    return dict(SOURCES[name])


def get_live_approved_sources():
    approved = []

    for key, source in SOURCES.items():
        if not source["permission_verified"]:
            continue

        if not source["automated_access_allowed"]:
            continue

        if not source["commercial_use_allowed"]:
            continue

        if not source["coverage_verified"]:
            continue

        if source["status"] != "APPROVED":
            continue

        approved.append(key)

    return approved


if __name__ == "__main__":
    print("MARKET SOURCE REGISTRY")

    for key, source in SOURCES.items():
        print(
            key,
            source["status"],
        )

    approved = get_live_approved_sources()

    print("LIVE APPROVED:", approved)

    if not approved:
        print(
            "LIVE PROVIDER: NOT AVAILABLE"
        )
