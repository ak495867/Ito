#include "../../cpp/ito_execution/order_state_machine.hpp"
#include "../../cpp/ito_observability/metrics_registry.hpp"
#include "../../cpp/ito_risk/limit_snapshot.hpp"
#include "../../cpp/ito_session/lease_fencer.hpp"

#include <cassert>

int main() {
    ito::session::LeaseFencer fencer;
    assert(fencer.acquire(5, 11, "node-a", 10, 100));
    assert(!fencer.acquire(5, 11, "node-b", 20, 100));
    assert(fencer.owns(5, 11, "node-a", 50));
    assert(fencer.renew("node-a", 50, 100));
    assert(fencer.release("node-a"));

    ito::execution::OrderStateMachine state(9001, 10);
    assert(state.apply(ito::execution::OrderEvent::RiskApprove));
    assert(state.apply(ito::execution::OrderEvent::Submit));
    assert(state.apply(ito::execution::OrderEvent::VenueAccept));
    assert(state.apply(ito::execution::OrderEvent::Fill, 4));
    assert(!state.terminal() && state.filled_quantity() == 4 && state.remaining_quantity() == 6);
    assert(state.apply(ito::execution::OrderEvent::Fill, 6));
    assert(state.terminal() && state.filled_quantity() == 10 && state.remaining_quantity() == 0);
    assert(!state.apply(ito::execution::OrderEvent::RecoveryRequired));

    ito::risk::LimitSnapshotGuard limits;
    assert(!limits.activate(ito::risk::LimitSnapshot{1, 100, 10, 1000, 100, 10, true, true}, 100));
    assert(limits.activate(ito::risk::LimitSnapshot{1, 200, 10, 1000, 100, 10, true, true}, 100));
    assert(limits.valid(150));
    assert(!limits.activate(ito::risk::LimitSnapshot{1, 300, 10, 1000, 100, 10, true, true}, 150));

    ito::observability::MetricsRegistry metrics;
    metrics.observe_latency("venue-5", 10);
    metrics.observe_latency("venue-5", 20);
    metrics.observe_latency("venue-5", 30);
    metrics.error("venue-5");
    const auto snapshot = metrics.snapshot("venue-5");
    assert(snapshot.count == 3 && snapshot.errors == 1 && snapshot.p50_ns == 20 && snapshot.p99_ns == 30);
    return 0;
}
