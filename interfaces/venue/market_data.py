from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass(frozen=True)
class Quote:
    instrument_id: str
    sequence: int
    timestamp_ns: int
    bid_ticks: int
    ask_ticks: int

    def validate(self) -> None:
        if not self.instrument_id:
            raise ValueError("instrument_id_invalid")
        if self.sequence <= 0:
            raise ValueError("sequence_invalid")
        if self.timestamp_ns <= 0:
            raise ValueError("timestamp_invalid")
        if self.bid_ticks <= 0 or self.ask_ticks < self.bid_ticks:
            raise ValueError("quote_prices_invalid")


class MarketDataFeed(Protocol):
    def quotes(self) -> Iterator[Quote]: ...
    def close(self) -> None: ...


class SimulatedMarketDataFeed:
    def __init__(self, quotes: list[Quote]) -> None:
        self._quotes = tuple(quotes)
        seen: set[tuple[str, int]] = set()
        for quote in self._quotes:
            quote.validate()
            key = (quote.instrument_id, quote.sequence)
            if key in seen:
                raise ValueError("duplicate_quote_sequence")
            seen.add(key)
        self._closed = False

    def quotes(self) -> Iterator[Quote]:
        if self._closed:
            raise RuntimeError("feed_closed")
        yield from self._quotes

    def close(self) -> None:
        self._closed = True
