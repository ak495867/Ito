from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class InstrumentSpec:
    instrument_id: int
    symbol: str = ""
    tick_size: float = 1.0
    multiplier: float = 1.0
    base_currency: str = "USD"
    maker_fee_bps: float = 0.0
    taker_fee_bps: float = 0.0
    clearing_fee_per_unit: float = 0.0
    borrow_fee_annual_bps: float = 0.0
    locate_required: bool = False


@dataclass(frozen=True)
class QuoteMark:
    bid_ticks: int
    ask_ticks: int
    timestamp_ns: int = 0

    @property
    def mid_ticks(self) -> float:
        return (self.bid_ticks + self.ask_ticks) / 2.0


@dataclass(frozen=True)
class FactorModel:
    factors: list[str]
    loadings: dict[int, dict[str, float]]
    covariance_matrix: dict[str, dict[str, float]]
    specific_variance: dict[int, float] = field(default_factory=dict)

    def calculate_variance(self, notionals: Mapping[int, float]) -> float:
        factor_exposures = {f: 0.0 for f in self.factors}
        for iid, notional in notionals.items():
            inst_loadings = self.loadings.get(iid, {})
            for f in self.factors:
                factor_exposures[f] += notional * inst_loadings.get(f, 0.0)

        factor_var = 0.0
        for f1 in self.factors:
            exp1 = factor_exposures[f1]
            if exp1 == 0.0:
                continue
            row = self.covariance_matrix.get(f1, {})
            for f2 in self.factors:
                exp2 = factor_exposures[f2]
                if exp2 == 0.0:
                    continue
                factor_var += exp1 * exp2 * row.get(f2, 0.0)

        spec_var = 0.0
        for iid, notional in notionals.items():
            var_eps = self.specific_variance.get(iid, 0.0)
            if var_eps > 0.0 and notional != 0.0:
                spec_var += (notional ** 2) * var_eps

        return max(0.0, factor_var + spec_var)

    def parametric_var(self, notionals: Mapping[int, float], confidence: float = 0.99) -> float:
        z = 2.3263 if confidence >= 0.99 else (1.6449 if confidence >= 0.95 else 1.2816)
        total_var = self.calculate_variance(notionals)
        return z * math.sqrt(total_var)

    def expected_shortfall(self, notionals: Mapping[int, float], confidence: float = 0.99) -> float:
        es_factor = 2.665 if confidence >= 0.99 else (2.063 if confidence >= 0.95 else 1.755)
        total_var = self.calculate_variance(notionals)
        return es_factor * math.sqrt(total_var)


@dataclass
class Position:
    quantity: int = 0
    average_price_ticks: float = 0.0
    realized_pnl_ticks: float = 0.0
    last_price_ticks: int = 0
    fees_paid_ticks: float = 0.0
    fees_paid_cash: float = 0.0
    realized_pnl_cash: float = 0.0
    borrowed_quantity: int = 0

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
    max_gross_notional_cash: float | None = None
    max_net_notional_cash: float | None = None
    max_concentration_cash: float | None = None
    max_loss_cash: float | None = None
    require_locates: bool = False
    max_expected_shortfall_cash: float | None = None
    max_parametric_var_cash: float | None = None


class PortfolioError(ValueError):
    pass


class Portfolio:
    def __init__(
        self,
        limits: PortfolioLimits,
        specs: Mapping[int, InstrumentSpec] | None = None,
        locates: Mapping[int, int] | None = None,
        factor_model: FactorModel | None = None,
    ) -> None:
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
        self.specs: dict[int, InstrumentSpec] = dict(specs) if specs else {}
        self.locates: dict[int, int] = dict(locates) if locates else {}
        self.factor_model = factor_model
        self.positions: dict[int, Position] = {}

    def _spec(self, instrument_id: int) -> InstrumentSpec:
        return self.specs.get(
            instrument_id,
            InstrumentSpec(instrument_id=instrument_id, symbol=str(instrument_id)),
        )

    def register_locate(self, instrument_id: int, quantity: int) -> None:
        if instrument_id <= 0 or quantity <= 0:
            raise PortfolioError("locate_invalid")
        self.locates[instrument_id] = self.locates.get(instrument_id, 0) + quantity

    def _position(self, instrument_id: int) -> Position:
        if instrument_id <= 0:
            raise PortfolioError("instrument_invalid")
        return self.positions.setdefault(instrument_id, Position())

    def apply_fill(
        self,
        instrument_id: int,
        side: int,
        quantity: int,
        price_ticks: int,
        is_taker: bool = True,
    ) -> Position:
        if side not in (-1, 1) or quantity <= 0 or price_ticks <= 0:
            raise PortfolioError("fill_invalid")
        position = self._position(instrument_id)
        spec = self._spec(instrument_id)

        is_short_opening = side < 0 and (position.quantity - quantity < 0)
        if is_short_opening:
            if not self.limits.allow_short:
                raise PortfolioError("short_sale_disabled")
            if self.limits.require_locates or spec.locate_required:
                current_short = max(0, -position.quantity)
                new_short = abs(min(0, position.quantity - quantity))
                short_increase = new_short - current_short
                available_locates = self.locates.get(instrument_id, 0)
                if short_increase > available_locates:
                    raise PortfolioError("short_locate_insufficient")
                self.locates[instrument_id] = available_locates - short_increase

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
            ) / total_quantity
            position.quantity = old_quantity + signed_quantity
        else:
            closing_quantity = min(abs(old_quantity), quantity)
            pnl_ticks = (
                closing_quantity * (price_ticks - old_average)
                if old_quantity > 0
                else closing_quantity * (old_average - price_ticks)
            )
            position.realized_pnl_ticks += pnl_ticks
            position.realized_pnl_cash += pnl_ticks * spec.tick_size * spec.multiplier
            position.quantity = old_quantity + signed_quantity
            if position.quantity == 0:
                position.average_price_ticks = 0.0
            elif abs(signed_quantity) > abs(old_quantity):
                position.average_price_ticks = float(price_ticks)

        position.last_price_ticks = price_ticks

        fee_bps = spec.taker_fee_bps if is_taker else spec.maker_fee_bps
        fee_cash = (
            quantity * price_ticks * spec.tick_size * spec.multiplier * (fee_bps / 10000.0)
            + quantity * spec.clearing_fee_per_unit
        )
        fee_ticks = fee_cash / (spec.tick_size * spec.multiplier) if (spec.tick_size * spec.multiplier) > 0 else 0.0
        position.fees_paid_ticks += fee_ticks
        position.fees_paid_cash += fee_cash

        avg_price_ret = (
            int(round(position.average_price_ticks))
            if float(position.average_price_ticks).is_integer()
            else position.average_price_ticks
        )
        pnl_ticks_ret = (
            int(round(position.realized_pnl_ticks))
            if float(position.realized_pnl_ticks).is_integer()
            else position.realized_pnl_ticks
        )

        return Position(
            position.quantity,
            avg_price_ret,
            pnl_ticks_ret,
            position.last_price_ticks,
            position.fees_paid_ticks,
            position.fees_paid_cash,
            position.realized_pnl_cash,
            position.borrowed_quantity,
        )

    def validate_order(
        self,
        instrument_id: int,
        side: int,
        quantity: int,
        price_ticks: int,
        is_taker: bool = True,
    ) -> tuple[bool, str]:
        if side not in (-1, 1) or quantity <= 0 or price_ticks <= 0:
            return False, "order_invalid"
        self._position(instrument_id)
        spec = self._spec(instrument_id)

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

        if side < 0 and current.quantity - quantity < 0:
            if not self.limits.allow_short:
                return False, "short_sale_disabled"
            if self.limits.require_locates or spec.locate_required:
                current_short = max(0, -current.quantity)
                new_short = abs(min(0, current.quantity - quantity))
                short_increase = new_short - current_short
                if short_increase > self.locates.get(instrument_id, 0):
                    return False, "short_locate_insufficient"

        projected_notionals_cash: dict[int, float] = {}
        for iid, pos in self.positions.items():
            pos_spec = self._spec(iid)
            price = price_ticks if iid == instrument_id else pos.last_price_ticks
            qty = (pos.quantity + side * quantity) if iid == instrument_id else pos.quantity
            projected_notionals_cash[iid] = qty * price * pos_spec.tick_size * pos_spec.multiplier

        if self.limits.max_gross_notional_cash is not None:
            cash_gross = sum(abs(v) for v in projected_notionals_cash.values())
            if cash_gross > self.limits.max_gross_notional_cash:
                return False, "gross_notional_cash_limit"

        if self.factor_model is not None:
            if self.limits.max_expected_shortfall_cash is not None:
                es = self.factor_model.expected_shortfall(projected_notionals_cash)
                if es > self.limits.max_expected_shortfall_cash:
                    return False, "expected_shortfall_limit"
            if self.limits.max_parametric_var_cash is not None:
                var = self.factor_model.parametric_var(projected_notionals_cash)
                if var > self.limits.max_parametric_var_cash:
                    return False, "parametric_var_limit"

        return True, "approved"

    def snapshot(
        self,
        prices: Mapping[int, int | QuoteMark] | None = None,
        mark_method: str = "last",
        current_time_ns: int | None = None,
        max_stale_ns: int | None = None,
    ) -> dict[str, object]:
        marks = prices or {}
        net_position = sum(position.quantity for position in self.positions.values())
        gross_position = sum(
            position.gross_quantity for position in self.positions.values()
        )
        gross_notional = 0
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        concentration: dict[str, int] = {}

        gross_notional_cash = 0.0
        net_notional_cash = 0.0
        realized_pnl_cash = 0.0
        unrealized_pnl_cash = 0.0
        total_fees_paid_cash = 0.0
        stale_positions: list[int] = []
        current_notionals_cash: dict[int, float] = {}

        for instrument_id, position in self.positions.items():
            spec = self._spec(instrument_id)
            price_input = marks.get(instrument_id, position.last_price_ticks)

            mark_val: float
            if isinstance(price_input, QuoteMark):
                if (
                    current_time_ns is not None
                    and max_stale_ns is not None
                    and (current_time_ns - price_input.timestamp_ns) > max_stale_ns
                ):
                    stale_positions.append(instrument_id)

                if mark_method == "mid":
                    mark_val = price_input.mid_ticks
                elif mark_method == "liquidation":
                    mark_val = float(price_input.bid_ticks if position.quantity >= 0 else price_input.ask_ticks)
                else:
                    mark_val = float(price_input.ask_ticks if position.quantity > 0 else price_input.bid_ticks)
            else:
                mark_val = float(price_input)

            if mark_val <= 0 and position.quantity != 0:
                raise PortfolioError("mark_invalid")

            pos_notional_ticks = int(position.gross_quantity * mark_val)
            gross_notional += pos_notional_ticks
            realized_pnl += position.realized_pnl_ticks
            pos_unrealized_ticks = 0.0
            if position.quantity > 0:
                pos_unrealized_ticks = position.quantity * (mark_val - position.average_price_ticks)
            elif position.quantity < 0:
                pos_unrealized_ticks = abs(position.quantity) * (position.average_price_ticks - mark_val)

            unrealized_pnl += pos_unrealized_ticks
            concentration[str(instrument_id)] = pos_notional_ticks

            unit_value = spec.tick_size * spec.multiplier
            pos_cash_notional = position.quantity * mark_val * unit_value
            current_notionals_cash[instrument_id] = pos_cash_notional
            gross_notional_cash += position.gross_quantity * mark_val * unit_value
            net_notional_cash += pos_cash_notional
            realized_pnl_cash += position.realized_pnl_cash
            unrealized_pnl_cash += pos_unrealized_ticks * unit_value
            total_fees_paid_cash += position.fees_paid_cash

        realized_ticks_int = int(round(realized_pnl))
        unrealized_ticks_int = int(round(unrealized_pnl))
        loss_ticks_int = -(realized_ticks_int + unrealized_ticks_int)
        top_concentration = max(concentration.values(), default=0)

        factor_metrics: dict[str, float] = {}
        if self.factor_model is not None:
            factor_metrics["portfolio_variance"] = self.factor_model.calculate_variance(current_notionals_cash)
            factor_metrics["parametric_var_cash"] = self.factor_model.parametric_var(current_notionals_cash)
            factor_metrics["expected_shortfall_cash"] = self.factor_model.expected_shortfall(current_notionals_cash)

        pos_dict: dict[str, object] = {}
        for instrument_id, pos in self.positions.items():
            item = pos.__dict__.copy()
            if float(item["average_price_ticks"]).is_integer():
                item["average_price_ticks"] = int(round(item["average_price_ticks"]))
            if float(item["realized_pnl_ticks"]).is_integer():
                item["realized_pnl_ticks"] = int(round(item["realized_pnl_ticks"]))
            pos_dict[str(instrument_id)] = item

        limits_breached = {
            "net_position": abs(net_position) > self.limits.max_net_position,
            "gross_position": gross_position > self.limits.max_gross_position,
            "gross_notional": gross_notional > self.limits.max_gross_notional_ticks,
            "concentration": top_concentration > self.limits.max_concentration_ticks,
            "loss": loss_ticks_int > self.limits.max_loss_ticks,
        }
        if self.factor_model is not None:
            if self.limits.max_expected_shortfall_cash is not None:
                limits_breached["expected_shortfall"] = (
                    factor_metrics.get("expected_shortfall_cash", 0.0) > self.limits.max_expected_shortfall_cash
                )
            if self.limits.max_parametric_var_cash is not None:
                limits_breached["parametric_var"] = (
                    factor_metrics.get("parametric_var_cash", 0.0) > self.limits.max_parametric_var_cash
                )

        res: dict[str, object] = {
            "net_position": net_position,
            "gross_position": gross_position,
            "gross_notional_ticks": gross_notional,
            "realized_pnl_ticks": realized_ticks_int,
            "unrealized_pnl_ticks": unrealized_ticks_int,
            "loss_ticks": loss_ticks_int,
            "gross_notional_cash": gross_notional_cash,
            "net_notional_cash": net_notional_cash,
            "realized_pnl_cash": realized_pnl_cash,
            "unrealized_pnl_cash": unrealized_pnl_cash,
            "total_fees_paid_cash": total_fees_paid_cash,
            "net_pnl_cash": realized_pnl_cash + unrealized_pnl_cash - total_fees_paid_cash,
            "stale_positions": stale_positions,
            "limits_breached": limits_breached,
            "positions": pos_dict,
        }
        if factor_metrics:
            res["factor_metrics"] = factor_metrics
        return res
