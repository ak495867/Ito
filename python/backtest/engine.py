from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Quote:
    timestamp_ns: int
    bid_ticks: int
    ask_ticks: int


@dataclass(frozen=True)
class Signal:
    timestamp_ns: int
    side: int
    quantity: int


@dataclass(frozen=True)
class Fill:
    timestamp_ns: int
    price_ticks: int
    quantity: int
    side: int


class ReplayBacktest:
    def __init__(self, max_position: int) -> None:
        if max_position <= 0:
            raise ValueError("max_position_invalid")
        self.max_position = max_position
        self.position = 0
        self.fills: list[Fill] = []

    def apply(self, quote: Quote, signal: Signal) -> Fill | None:
        if quote.timestamp_ns <= 0 or quote.bid_ticks <= 0 or quote.ask_ticks < quote.bid_ticks or signal.side not in (-1, 1):
            return None
        price = quote.ask_ticks if signal.side > 0 else quote.bid_ticks
        signed_quantity = signal.quantity if signal.side > 0 else -signal.quantity
        next_position = self.position + signed_quantity
        if signal.quantity <= 0 or abs(next_position) > self.max_position:
            return None
        fill = Fill(signal.timestamp_ns, price, signal.quantity, signal.side)
        self.position = next_position
        self.fills.append(fill)
        return fill

    def run(self, quotes: Iterable[Quote], signals: Iterable[Signal]) -> list[Fill]:
        quote_by_time: dict[int, Quote] = {}
        for quote in quotes:
            if quote.timestamp_ns in quote_by_time:
                raise ValueError("duplicate_quote_timestamp")
            quote_by_time[quote.timestamp_ns] = quote
        for signal in signals:
            quote = quote_by_time.get(signal.timestamp_ns)
            if quote is not None:
                self.apply(quote, signal)
        return list(self.fills)
