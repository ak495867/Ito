from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Quote:
    timestamp_ns: int
    bid_ticks: int
    ask_ticks: int
    bid_size: int = 100
    ask_size: int = 100
    bids: list[tuple[int, int]] | None = None
    asks: list[tuple[int, int]] | None = None


@dataclass(frozen=True)
class Signal:
    timestamp_ns: int
    side: int
    quantity: int
    order_type: str = "market"
    limit_price_ticks: int | None = None
    latency_ns: int = 0


@dataclass(frozen=True)
class Fill:
    timestamp_ns: int
    price_ticks: int
    quantity: int
    side: int
    is_maker: bool = False
    fee_ticks: float = 0.0
    slippage_ticks: int = 0
    latency_ns: int = 0
    adverse_selection_cost_ticks: float = 0.0


@dataclass(frozen=True)
class MarketTrade:
    timestamp_ns: int
    price_ticks: int
    quantity: int
    aggressor_side: int


class ReplayBacktest:
    def __init__(self, max_position: int, strict_unique_timestamps: bool = True) -> None:
        if max_position <= 0:
            raise ValueError("max_position_invalid")
        self.max_position = max_position
        self.strict_unique_timestamps = strict_unique_timestamps
        self.position = 0
        self.fills: list[Fill] = []

    def apply(self, quote: Quote, signal: Signal) -> Fill | None:
        if (
            quote.timestamp_ns <= 0
            or quote.bid_ticks <= 0
            or quote.ask_ticks < quote.bid_ticks
            or signal.side not in (-1, 1)
        ):
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
            if self.strict_unique_timestamps and quote.timestamp_ns in quote_by_time:
                raise ValueError("duplicate_quote_timestamp")
            quote_by_time[quote.timestamp_ns] = quote
        for signal in signals:
            quote = quote_by_time.get(signal.timestamp_ns)
            if quote is not None:
                self.apply(quote, signal)
        return list(self.fills)


@dataclass
class BookLevel:
    price_ticks: int
    size: int


class L2OrderBook:
    def __init__(self) -> None:
        self.bids: list[BookLevel] = []
        self.asks: list[BookLevel] = []

    def update_from_quote(self, quote: Quote) -> None:
        if quote.bids:
            self.bids = [BookLevel(p, s) for p, s in sorted(quote.bids, key=lambda x: -x[0])]
        else:
            self.bids = [BookLevel(quote.bid_ticks, quote.bid_size)]

        if quote.asks:
            self.asks = [BookLevel(p, s) for p, s in sorted(quote.asks, key=lambda x: x[0])]
        else:
            self.asks = [BookLevel(quote.ask_ticks, quote.ask_size)]

    @property
    def best_bid(self) -> int:
        return self.bids[0].price_ticks if self.bids else 0

    @property
    def best_ask(self) -> int:
        return self.asks[0].price_ticks if self.asks else 0

    @property
    def mid_price(self) -> float:
        if self.best_bid > 0 and self.best_ask > 0:
            return (self.best_bid + self.best_ask) / 2.0
        return float(self.best_bid or self.best_ask)

    @property
    def spread(self) -> int:
        return max(0, self.best_ask - self.best_bid)


@dataclass
class RestingOrder:
    order_id: int
    placed_time_ns: int
    arrival_time_ns: int
    side: int
    price_ticks: int
    remaining_quantity: int
    queue_ahead: int
    is_post_only: bool = False


@dataclass(frozen=True)
class MicrostructureConfig:
    wire_latency_ns: int = 500
    engine_latency_ns: int = 250
    maker_fee_bps: float = -0.1
    taker_fee_bps: float = 0.3
    queue_cancellation_rate: float = 0.2
    adverse_selection_alpha: float = 0.4


class MicrostructureEngine:
    def __init__(
        self,
        max_position: int,
        config: MicrostructureConfig | None = None,
    ) -> None:
        if max_position <= 0:
            raise ValueError("max_position_invalid")
        self.max_position = max_position
        self.config = config or MicrostructureConfig()
        self.book = L2OrderBook()
        self.position = 0
        self.fills: list[Fill] = []
        self.resting_orders: list[RestingOrder] = []
        self._next_order_id = 1
        self.current_time_ns = 0

    def on_quote(self, quote: Quote) -> list[Fill]:
        if (
            quote.timestamp_ns <= 0
            or quote.bid_ticks <= 0
            or quote.ask_ticks < quote.bid_ticks
        ):
            return []
        self.current_time_ns = max(self.current_time_ns, quote.timestamp_ns)
        self.book.update_from_quote(quote)
        return self._evaluate_resting_orders(quote)

    def on_market_trade(self, trade: MarketTrade) -> list[Fill]:
        self.current_time_ns = max(self.current_time_ns, trade.timestamp_ns)
        new_fills: list[Fill] = []
        surviving_orders: list[RestingOrder] = []

        for order in self.resting_orders:
            if order.arrival_time_ns > trade.timestamp_ns:
                surviving_orders.append(order)
                continue

            matches_bid = (order.side > 0 and trade.aggressor_side < 0 and trade.price_ticks <= order.price_ticks)
            matches_ask = (order.side < 0 and trade.aggressor_side > 0 and trade.price_ticks >= order.price_ticks)

            if matches_bid or matches_ask:
                decayed_queue = int(order.queue_ahead * (1.0 - self.config.queue_cancellation_rate))
                if trade.quantity > decayed_queue:
                    fill_qty = min(order.remaining_quantity, trade.quantity - decayed_queue)
                    signed_fill = fill_qty if order.side > 0 else -fill_qty
                    if abs(self.position + signed_fill) <= self.max_position and fill_qty > 0:
                        self.position += signed_fill
                        order.remaining_quantity -= fill_qty
                        adv_cost = self.config.adverse_selection_alpha * self.book.spread
                        fill = Fill(
                            timestamp_ns=trade.timestamp_ns,
                            price_ticks=order.price_ticks,
                            quantity=fill_qty,
                            side=order.side,
                            is_maker=True,
                            fee_ticks=fill_qty * order.price_ticks * (self.config.maker_fee_bps / 10000.0),
                            slippage_ticks=0,
                            latency_ns=trade.timestamp_ns - order.placed_time_ns,
                            adverse_selection_cost_ticks=adv_cost,
                        )
                        self.fills.append(fill)
                        new_fills.append(fill)
                else:
                    order.queue_ahead = max(0, decayed_queue - trade.quantity)

            if order.remaining_quantity > 0:
                surviving_orders.append(order)

        self.resting_orders = surviving_orders
        return new_fills

    def submit_order(self, signal: Signal) -> list[Fill]:
        if signal.side not in (-1, 1) or signal.quantity <= 0:
            return []

        latency = signal.latency_ns or (self.config.wire_latency_ns + self.config.engine_latency_ns)
        arrival_time = signal.timestamp_ns + latency
        self.current_time_ns = max(self.current_time_ns, arrival_time)

        order_type = signal.order_type.lower()
        if order_type == "market":
            return self._execute_aggressive(signal, arrival_time, latency)
        elif order_type in ("limit", "post_only"):
            return self._place_limit(signal, arrival_time, latency, is_post_only=(order_type == "post_only"))
        return []

    def _execute_aggressive(self, signal: Signal, arrival_time: int, latency: int) -> list[Fill]:
        ladder = self.book.asks if signal.side > 0 else self.book.bids
        if not ladder:
            return []

        remaining = signal.quantity
        fills_generated: list[Fill] = []
        arrival_mid = self.book.mid_price

        for level in ladder:
            if remaining <= 0:
                break
            available = level.size
            if available <= 0:
                continue

            match_qty = min(remaining, available)
            signed_qty = match_qty if signal.side > 0 else -match_qty
            if abs(self.position + signed_qty) > self.max_position:
                break

            self.position += signed_qty
            remaining -= match_qty
            level.size -= match_qty

            slippage = abs(level.price_ticks - int(arrival_mid))
            fee = match_qty * level.price_ticks * (self.config.taker_fee_bps / 10000.0)
            fill = Fill(
                timestamp_ns=arrival_time,
                price_ticks=level.price_ticks,
                quantity=match_qty,
                side=signal.side,
                is_maker=False,
                fee_ticks=fee,
                slippage_ticks=slippage,
                latency_ns=latency,
                adverse_selection_cost_ticks=0.0,
            )
            self.fills.append(fill)
            fills_generated.append(fill)

        return fills_generated

    def _place_limit(
        self, signal: Signal, arrival_time: int, latency: int, is_post_only: bool
    ) -> list[Fill]:
        limit_price = signal.limit_price_ticks
        if limit_price is None:
            limit_price = self.book.best_bid if signal.side > 0 else self.book.best_ask

        crosses = (signal.side > 0 and limit_price >= self.book.best_ask and self.book.best_ask > 0) or (
            signal.side < 0 and limit_price <= self.book.best_bid and self.book.best_bid > 0
        )
        if crosses:
            if is_post_only:
                return []
            return self._execute_aggressive(signal, arrival_time, latency)

        queue_ahead = 0
        ladder = self.book.bids if signal.side > 0 else self.book.asks
        for level in ladder:
            if level.price_ticks == limit_price:
                queue_ahead = level.size
                break

        order = RestingOrder(
            order_id=self._next_order_id,
            placed_time_ns=signal.timestamp_ns,
            arrival_time_ns=arrival_time,
            side=signal.side,
            price_ticks=limit_price,
            remaining_quantity=signal.quantity,
            queue_ahead=queue_ahead,
            is_post_only=is_post_only,
        )
        self._next_order_id += 1
        self.resting_orders.append(order)
        return []

    def _evaluate_resting_orders(self, quote: Quote) -> list[Fill]:
        new_fills: list[Fill] = []
        surviving: list[RestingOrder] = []

        for order in self.resting_orders:
            if order.arrival_time_ns > quote.timestamp_ns:
                surviving.append(order)
                continue

            should_fill = False
            fill_price = order.price_ticks
            if order.side > 0 and quote.ask_ticks <= order.price_ticks:
                should_fill = True
                fill_price = quote.ask_ticks
            elif order.side < 0 and quote.bid_ticks >= order.price_ticks:
                should_fill = True
                fill_price = quote.bid_ticks

            if should_fill:
                signed = order.remaining_quantity if order.side > 0 else -order.remaining_quantity
                if abs(self.position + signed) <= self.max_position:
                    self.position += signed
                    adv_cost = self.config.adverse_selection_alpha * max(1, quote.ask_ticks - quote.bid_ticks)
                    fill = Fill(
                        timestamp_ns=quote.timestamp_ns,
                        price_ticks=fill_price,
                        quantity=order.remaining_quantity,
                        side=order.side,
                        is_maker=True,
                        fee_ticks=order.remaining_quantity * fill_price * (self.config.maker_fee_bps / 10000.0),
                        slippage_ticks=0,
                        latency_ns=quote.timestamp_ns - order.placed_time_ns,
                        adverse_selection_cost_ticks=adv_cost,
                    )
                    self.fills.append(fill)
                    new_fills.append(fill)
                    continue

            surviving.append(order)

        self.resting_orders = surviving
        return new_fills

    def run_simulation(
        self,
        events: list[Quote | MarketTrade | Signal],
    ) -> list[Fill]:
        sorted_events = sorted(
            events,
            key=lambda e: (e.timestamp_ns, 0 if isinstance(e, Quote) else (1 if isinstance(e, MarketTrade) else 2)),
        )
        for ev in sorted_events:
            if isinstance(ev, Quote):
                self.on_quote(ev)
            elif isinstance(ev, MarketTrade):
                self.on_market_trade(ev)
            elif isinstance(ev, Signal):
                self.submit_order(ev)
        return list(self.fills)
