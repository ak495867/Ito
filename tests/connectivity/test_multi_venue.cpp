#include "../../cpp/ito_connectivity/simulator_adapter.hpp"
#include "../../cpp/ito_routing/smart_order_router.hpp"

#include <cassert>
#include <memory>

int main() {
    ito::core::EventJournal journal;
    ito::session::SessionManager sessions;
    const ito::connectivity::VenueIdentity exchange_identity{5, 8, ito::connectivity::VenueKind::Exchange, ito::connectivity::AdapterProtocol::Simulator, "exchange-a", "us"};
    const ito::connectivity::VenueIdentity broker_identity{6, 9, ito::connectivity::VenueKind::Broker, ito::connectivity::AdapterProtocol::Simulator, "broker-b", "uk"};
    auto exchange_adapter = std::make_unique<ito::connectivity::SimulatorAdapter>(journal, exchange_identity);
    auto* exchange_adapter_ptr = exchange_adapter.get();
    assert(sessions.add(std::move(exchange_adapter), 1));
    assert(sessions.add(std::make_unique<ito::connectivity::SimulatorAdapter>(journal, broker_identity), 1));
    assert(sessions.connect(5, 2));
    assert(sessions.connect(6, 2));
    auto statuses = sessions.statuses();
    assert(statuses.size() == 2);
    const ito::connectivity::NormalizedOrder order{1001, 1001, 101, 201, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 100, 10, 7};
    ito::routing::SmartOrderRouter router(sessions, ito::routing::RoutingPolicy{100, 500, true});
    const std::vector<ito::routing::RouteCandidate> candidates{{5, 8, 100, 100, 2, 1, true, true, true}, {6, 9, 100, 100, 3, 2, true, true, true}};
    const auto first = router.submit(order, candidates, 3);
    assert(first.has_value() && first->route.venue_id == 5);
    const auto cancelled = exchange_adapter_ptr->cancel(order.client_order_id, 4);
    assert(cancelled.has_value() && cancelled->status == ito::connectivity::ExecutionStatus::Cancelled);
    assert(sessions.disconnect(5, 4));
    const auto second = router.submit(order, candidates, 5);
    assert(second.has_value() && second->route.venue_id == 6);
    return 0;
}
