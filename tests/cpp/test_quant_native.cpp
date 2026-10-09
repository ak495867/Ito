#include "../../cpp/ito_execution/zero_alloc_book.hpp"
#include "../../cpp/ito_execution/queue_tracker.hpp"
#include "../../cpp/ito_risk/hardware_risk_bridge.hpp"
#include "../../cpp/ito_routing/smart_order_router.hpp"

#include <cassert>
#include <iostream>

int main() {
    ito::execution::ZeroAllocOrderBook<16> book;
    book.update_bid(100, 50, 1);
    book.update_bid(99, 100, 2);
    book.update_ask(102, 40, 1);
    book.update_ask(103, 60, 2);

    assert(book.best_bid() == 100);
    assert(book.best_ask() == 102);
    assert(book.mid_price() == 101);
    assert(book.spread() == 2);

    const auto walk = book.walk_book(true, 70);
    assert(walk.executed_quantity == 70);
    assert(walk.levels_consumed == 2);
    assert(walk.vwap_ticks == 102);
    assert(walk.slippage_ticks == 1);

    auto resting = ito::execution::QueueTracker::create_order(101, true, 100, 10, 50);
    assert(resting.queue_ahead == 50);

    const auto fill1 = ito::execution::QueueTracker::process_trade(resting, 100, 30, 0.0);
    assert(fill1 == 0);
    assert(resting.queue_ahead == 20);

    const auto fill2 = ito::execution::QueueTracker::process_trade(resting, 100, 25, 0.0);
    assert(fill2 == 5);
    assert(resting.remaining_quantity == 5);
    assert(resting.queue_ahead == 0);

    ito::risk::HardwareRiskGateModel hw_gate;
    hw_gate.reset();

    ito::risk::HardwareGateInputs in;
    in.intent_valid = true;
    in.side_buy = true;
    in.trading_enabled = true;
    in.limits_valid = true;
    in.clock_healthy = true;
    in.feed_healthy = true;
    in.halted = false;
    in.price_ticks = 100;
    in.quantity = 10;
    in.max_quantity = 50;
    in.max_notional_ticks = 5000;
    in.net_position = 0;
    in.max_net_position = 100;

    const auto out0 = hw_gate.step(in);
    assert(!out0.decision_valid);

    const auto out1 = hw_gate.step(in);
    assert(out1.decision_valid);
    assert(out1.approved);
    assert(out1.reason_code == ito::risk::HardwareReasonCode::Approved);

    in.quantity = 100;
    hw_gate.step(in);
    const auto out2 = hw_gate.step(in);
    assert(out2.decision_valid);
    assert(!out2.approved);
    assert(out2.reason_code == ito::risk::HardwareReasonCode::QuantityLimit);

    return 0;
}
