#include "ito_connectivity/endpoint_connector.hpp"
#include "ito_connectivity/network_adapter.hpp"

#include <cassert>
#include <chrono>
#include <iostream>
#include <thread>

int main() {
    ito::connectivity::VenueIdentity venue_id{};
    venue_id.venue_id = 5;
    venue_id.broker_id = 1;

    ito::connectivity::SessionConfig session{};
    session.branch_id = 1001;
    session.venue = venue_id;
    session.live_enabled = false;

    ito::connectivity::EndpointConnectorConfig endpoint{};
    endpoint.host = "127.0.0.1";
    endpoint.port = 12345;
    endpoint.tls_required = false;
    endpoint.live_enabled = false;

    ito::connectivity::NetworkVenueAdapter adapter(session, endpoint);
    assert(adapter.status() == ito::connectivity::SessionStatus::Disabled);

    ito::connectivity::NormalizedOrder order{};
    order.correlation_id = 1;
    order.client_order_id = 100;
    order.instrument_id = 1001;
    order.account_id = 1;
    order.side = ito::protocol::Side::Buy;
    order.order_type = ito::protocol::OrderType::Limit;
    order.time_in_force = ito::protocol::TimeInForce::Day;
    order.price_ticks = 50;
    order.quantity = 100;
    order.strategy_id = 7;

    auto report = adapter.submit(order, 1000);
    assert(!report.has_value());

    adapter.disconnect(2000);
    assert(adapter.status() == ito::connectivity::SessionStatus::Disabled);

    return 0;
}
