#include "../../cpp/ito_connectivity/simulator_adapter.hpp"
#include "../../cpp/ito_routing/smart_order_router.hpp"

#include <iostream>
#include <memory>

int main() {
    ito::core::EventJournal journal;
    ito::session::SessionManager sessions;
    sessions.add(std::make_unique<ito::connectivity::SimulatorAdapter>(journal, ito::connectivity::VenueIdentity{5, 8, ito::connectivity::VenueKind::Exchange, ito::connectivity::AdapterProtocol::Simulator, "exchange-a", "us"}), 1);
    sessions.add(std::make_unique<ito::connectivity::SimulatorAdapter>(journal, ito::connectivity::VenueIdentity{6, 9, ito::connectivity::VenueKind::Broker, ito::connectivity::AdapterProtocol::Simulator, "broker-b", "uk"}), 1);
    sessions.connect(5, 2);
    sessions.connect(6, 2);
    ito::routing::SmartOrderRouter router(sessions, ito::routing::RoutingPolicy{100, 500, true});
    const ito::connectivity::NormalizedOrder order{5001, 5001, 101, 201, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 100, 10, 7};
    const std::vector<ito::routing::RouteCandidate> candidates{{5, 8, 100, 100, 2, 1, true, true, true}, {6, 9, 100, 100, 3, 2, true, true, true}};
    const auto route = router.submit(order, candidates, 3);
    if (!route.has_value()) {
        return 1;
    }
    std::cout << "route_venue=" << route->route.venue_id << '\n';
    return 0;
}
