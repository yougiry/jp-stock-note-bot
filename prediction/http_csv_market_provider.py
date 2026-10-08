"""
HTTP CSV Market Data Provider
Prediction Engine v5.11

Generic provider for an explicitly permitted
HTTP/CSV market-data source.

Important:
- Does not assume any specific vendor.
- Does not bypass authentication or access controls.
- Does not fabricate missing data.
- Permission flags must be supplied explicitly.
"""

import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

try:
    from prediction.market_provider import (
        MarketDataBatch,
        MarketDataProvider,
    )
except ImportError:
    from market_provider import (
        MarketDataBatch,
        MarketDataProvider,
    )


JST = ZoneInfo("Asia/Tokyo")


class HttpCsvMarketProvider(MarketDataProvider):

    def __init__(
        self,
        source_name,
        url,
        automated_access_allowed=False,
        commercial_use_allowed=False,
        headers=None,
        timeout=(10, 60),
    ):
        if not source_name:
            raise ValueError(
                "source_name is required"
            )

        if not url:
            raise ValueError(
                "url is required"
            )

        self.source_name = source_name
        self.url = url

        self.automated_access_allowed = (
            automated_access_allowed
        )

        self.commercial_use_allowed = (
            commercial_use_allowed
        )

        self.headers = headers or {}
        self.timeout = timeout

    def fetch_daily_bars(
        self,
        codes,
        trading_date,
    ):
        """
        Fetch a CSV dataset and retain only
        requested security codes and trading date.

        Expected CSV columns:

        code
        date
        open
        high
        low
        close
        volume

        Optional:
        turnover
        publication_at
        """

        if not self.automated_access_allowed:
            raise PermissionError(
                "Automated access has not "
                "been approved for this source"
            )

        if not self.commercial_use_allowed:
            raise PermissionError(
                "Commercial use has not "
                "been approved for this source"
            )

        wanted_codes = {
            str(code).strip()
            for code in codes
            if str(code).strip()
        }

        if not wanted_codes:
            raise ValueError(
                "No security codes supplied"
            )

        response = requests.get(
            self.url,
            headers=self.headers,
            timeout=self.timeout,
        )

        response.raise_for_status()

        retrieved_at = datetime.now(
            JST
        ).isoformat()

        reader = csv.DictReader(
            io.StringIO(response.text)
        )

        required_columns = {
            "code",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

        fieldnames = set(
            reader.fieldnames or []
        )

        missing_columns = (
            required_columns - fieldnames
        )

        if missing_columns:
            raise ValueError(
                "CSV missing required columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        records = []

        for row in reader:

            code = str(
                row.get("code", "")
            ).strip()

            row_date = str(
                row.get("date", "")
            ).strip()

            if code not in wanted_codes:
                continue

            if row_date != trading_date:
                continue

            records.append(
                {
                    "code": code,
                    "date": row_date,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "volume": row.get("volume"),
                    "turnover": row.get(
                        "turnover"
                    ),
                    "publication_at": row.get(
                        "publication_at"
                    ),
                }
            )

        return MarketDataBatch(
            source=self.source_name,
            retrieved_at=retrieved_at,
            records=records,
            automated_access_allowed=(
                self.automated_access_allowed
            ),
            commercial_use_allowed=(
                self.commercial_use_allowed
            ),
        )
