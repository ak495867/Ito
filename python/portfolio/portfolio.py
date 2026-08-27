from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass
class Position:
    quantity: int = 0
    average_price_ticks: int = 0
    realized_pnl_ticks: int = 0
    last_price_ticks: int = 0

    @property
    def gross_quantity(self) -> int:
        return abs(self.quantity)


@dataclass(frozen=True)
class PortfolioLimits:
    max_net_position: int
    max_gross_position: int
    max_gross_notional_ticks: int
    max_concentration_ticks: int
    max_loss_ticks: int
    allow_short: bool = False


class PortfolioError(ValueError):
    pass


class Portfolio:
    def __init__(self, limits: PortfolioLimits) -> None:
        if (
            min(
                limits.max_net_position,
                limits.max_gross_position,
                limits.max_gross_notional_ticks,
                limits.max_concentration_ticks,
            )
            <= 0
            or limits.max_loss_ticks < 0
        ):
            raise PortfolioError("limits_invalid")
        self.limits = limits
        self.positions: dict[int, Position] = {}

    def _position(self, instrument_id: int) -> Position:
        if instrument_id <= 0:
            raise PortfolioError("instrument_invalid")
        return self.positions.setdefault(instrument_id, Position())

    def apply_fill(
        self, instrument_id: int, side: int, quantity: int, price_ticks: int
    ) -> Position:
        if side not in (-1, 1) or quantity <= 0 or price_ticks <= 0:
            raise PortfolioError("fill_invalid")
        position = self._position(instrument_id)
        if (
            side < 0
            and position.quantity >= 0
            and quantity > position.quantity
            and not self.limits.allow_short
        ):
            raise PortfolioError("short_sale_disabled")
        signed_quantity = side * quantity
        old_quantity = position.quantity
        old_average = position.average_price_ticks
        if (
            old_quantity == 0
            or (old_quantity > 0 and signed_quantity > 0)
            or (old_quantity < 0 and signed_quantity < 0)
        ):
            total_quantity = abs(old_quantity) + quantity
            position.average_price_ticks = (
                abs(old_quantity) * old_average + quantity * price_ticks
            ) // total_quantity
            position.quantity = old_quantity + signed_quantity
        else:
            closing_quantity = min(abs(old_quantity), quantity)
            if old_quantity > 0:
                position.realized_pnl_ticks += closing_quantity * (
                    price_ticks - old_average
                )
            else:
                position.realized_pnl_ticks += closing_quantity * (
                    old_average - price_ticks
                )
            position.quantity = old_quantity + signed_quantity
            if position.quantity == 0:
                position.average_price_ticks = 0
            elif abs(signed_quantity) > abs(old_quantity):
                position.average_price_ticks = price_ticks
        position.last_price_ticks = price_ticks
        return Position(
            position.quantity,
            position.average_price_ticks,
            position.realized_pnl_ticks,
            position.last_price_ticks,
        )

    def validate_order(
        self, instrument_id: int, side: int, quantity: int, price_ticks: int
    ) -> tuple[bool, str]:
        if side not in (-1, 1) or quantity <= 0 or price_ticks <= 0:
            return False, "order_invalid"
        self._position(instrument_id)
        current_net = sum(position.quantity for position in self.positions.values())
        current_gross = sum(
            position.gross_quantity for position in self.positions.values()
        )
        current_notional = sum(
            position.gross_quantity * position.last_price_ticks
            for position in self.positions.values()
        )
        current = self.positions[instrument_id]
        projected_net = current_net + side * quantity
        projected_gross = (
            current_gross
            - current.gross_quantity
            + abs(current.quantity + side * quantity)
        )
        projected_notional = (
            current_notional
            - current.gross_quantity * current.last_price_ticks
            + abs(current.quantity + side * quantity) * price_ticks
        )
        if abs(projected_net) > self.limits.max_net_position:
            return False, "net_position_limit"
        if projected_gross > self.limits.max_gross_position:
            return False, "gross_position_limit"
        if projected_notional > self.limits.max_gross_notional_ticks:
            return False, "gross_notional_limit"
        projected_concentration = abs(current.quantity + side * quantity) * price_ticks
        if projected_concentration > self.limits.max_concentration_ticks:
            return False, "concentration_limit"
        if side < 0 and current.quantity - quantity < 0 and not self.limits.allow_short:
            return False, "short_sale_disabled"
        return True, "approved"

    def snapshot(self, prices: Mapping[int, int] | None = None) -> dict[str, object]:
        marks = prices or {}
        net_position = sum(position.quantity for position in self.positions.values())
        gross_position = sum(
            position.gross_quantity for position in self.positions.values()
        )
        gross_notional = 0
        realized_pnl = 0
        unrealized_pnl = 0
        concentration: dict[str, int] = {}
        for instrument_id, position in self.positions.items():
            mark = marks.get(instrument_id, position.last_price_ticks)
            if mark <= 0 and position.quantity != 0:
                raise PortfolioError("mark_invalid")
            gross_notional += position.gross_quantity * mark
            realized_pnl += position.realized_pnl_ticks
            if position.quantity > 0:
                unrealized_pnl += position.quantity * (
                    mark - position.average_price_ticks
                )
            elif position.quantity < 0:
                unrealized_pnl += abs(position.quantity) * (
                    position.average_price_ticks - mark
                )
            concentration[str(instrument_id)] = position.gross_quantity * mark
        loss_ticks = -(realized_pnl + unrealized_pnl)
        top_concentration = max(concentration.values(), default=0)
        return {
            "net_position": net_position,
            "gross_position": gross_position,
            "gross_notional_ticks": gross_notional,
            "realized_pnl_ticks": realized_pnl,
            "unrealized_pnl_ticks": unrealized_pnl,
            "loss_ticks": loss_ticks,
            "limits_breached": {
                "net_position": abs(net_position) > self.limits.max_net_position,
                "gross_position": gross_position > self.limits.max_gross_position,
                "gross_notional": gross_notional > self.limits.max_gross_notional_ticks,
                "concentration": top_concentration
                > self.limits.max_concentration_ticks,
                "loss": loss_ticks > self.limits.max_loss_ticks,
            },
            "positions": {
                str(instrument_id): position.__dict__.copy()
                for instrument_id, position in self.positions.items()
            },
        }
