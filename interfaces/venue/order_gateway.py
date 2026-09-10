from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Environment(str, Enum):
    SIMULATOR = "simulator"
    PAPER = "paper"
    SHADOW = "shadow"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderState(str, Enum):
    ACCEPTED = "accepted"
    CANCELED = "canceled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OrderRequest:
    client_order_id: int
    instrument_id: str
    side: OrderSide
    quantity: int
    price_ticks: int
    environment: Environment = Environment.SIMULATOR

    def validate(self) -> None:
        if self.client_order_id <= 0:
            raise ValueError("client_order_id_invalid")
        if not self.instrument_id:
            raise ValueError("instrument_id_invalid")
        if self.quantity <= 0:
            raise ValueError("quantity_invalid")
        if self.price_ticks <= 0:
            raise ValueError("price_ticks_invalid")
        if self.environment is Environment.LIVE:
            raise ValueError("live_execution_disabled")


@dataclass(frozen=True)
class OrderAck:
    client_order_id: int
    venue_order_id: str
    state: OrderState
    accepted_quantity: int
    reason: str = ""


class OrderGateway(Protocol):
    def submit(self, request: OrderRequest) -> OrderAck: ...
    def cancel(self, client_order_id: int) -> OrderAck: ...
    def close(self) -> None: ...


class SimulatedOrderGateway:
    def __init__(self, venue_id: int) -> None:
        if venue_id <= 0:
            raise ValueError("venue_id_invalid")
        self.venue_id = venue_id
        self._orders: dict[int, OrderAck] = {}
        self._closed = False

    def submit(self, request: OrderRequest) -> OrderAck:
        if self._closed:
            raise RuntimeError("gateway_closed")
        request.validate()
        if request.client_order_id in self._orders:
            return OrderAck(
                request.client_order_id,
                f"{self.venue_id}-{request.client_order_id}",
                OrderState.REJECTED,
                0,
                "duplicate_client_order_id",
            )
        ack = OrderAck(
            request.client_order_id,
            f"{self.venue_id}-{request.client_order_id}",
            OrderState.ACCEPTED,
            request.quantity,
        )
        self._orders[request.client_order_id] = ack
        return ack

    def cancel(self, client_order_id: int) -> OrderAck:
        if self._closed:
            raise RuntimeError("gateway_closed")
        existing = self._orders.get(client_order_id)
        if existing is None:
            return OrderAck(
                client_order_id,
                f"{self.venue_id}-{client_order_id}",
                OrderState.UNKNOWN,
                0,
                "order_not_found",
            )
        canceled = OrderAck(
            client_order_id,
            existing.venue_order_id,
            OrderState.CANCELED,
            0,
        )
        self._orders[client_order_id] = canceled
        return canceled

    def close(self) -> None:
        self._closed = True
