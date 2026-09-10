from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol

from interfaces.venue.order_gateway import OrderSide


@dataclass(frozen=True)
class ExecutionReport:
    execution_id: str
    client_order_id: int
    instrument_id: str
    side: OrderSide
    quantity: int
    price_ticks: int
    timestamp_ns: int

    def validate(self) -> None:
        if not self.execution_id:
            raise ValueError("execution_id_invalid")
        if self.client_order_id <= 0 or not self.instrument_id:
            raise ValueError("order_reference_invalid")
        if self.quantity <= 0 or self.price_ticks <= 0 or self.timestamp_ns <= 0:
            raise ValueError("execution_values_invalid")


class DropCopyFeed(Protocol):
    def reports(self) -> Iterator[ExecutionReport]: ...
    def close(self) -> None: ...


class SimulatedDropCopyFeed:
    def __init__(self, reports: list[ExecutionReport]) -> None:
        self._reports = tuple(reports)
        execution_ids: set[str] = set()
        for report in self._reports:
            report.validate()
            if report.execution_id in execution_ids:
                raise ValueError("duplicate_execution_id")
            execution_ids.add(report.execution_id)
        self._closed = False

    def reports(self) -> Iterator[ExecutionReport]:
        if self._closed:
            raise RuntimeError("drop_copy_closed")
        yield from self._reports

    def close(self) -> None:
        self._closed = True
