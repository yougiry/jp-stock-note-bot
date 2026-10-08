"""
Market Data Provider Interface
Prediction Engine v5.11

Provider implementations must:
- identify their data source
- return raw OHLCV records
- report retrieval timestamps
- declare usage permissions
- never fabricate missing prices
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MarketDataBatch:
    source: str
    retrieved_at: str
    records: list[dict[str, Any]]
    commercial_use_allowed: bool
    automated_access_allowed: bool


class MarketDataProvider(ABC):

    @abstractmethod
    def fetch_daily_bars(
        self,
        codes: list[str],
        trading_date: str,
    ) -> MarketDataBatch:
        """Fetch daily OHLCV records."""
        raise NotImplementedError


def validate_provider_permissions(
    batch: MarketDataBatch,
) -> None:

    if not batch.automated_access_allowed:
        raise PermissionError(
            "Automated data access is not permitted"
        )

    if not batch.commercial_use_allowed:
        raise PermissionError(
            "Commercial use is not permitted"
        )

    if not batch.source:
        raise ValueError(
            "Market data source is missing"
        )

    if not batch.retrieved_at:
        raise ValueError(
            "Retrieval timestamp is missing"
        )

    if not isinstance(batch.records, list):
        raise TypeError(
            "Market data records must be a list"
        )
