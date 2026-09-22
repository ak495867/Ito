#include "ito_connectivity/endpoint_connector.hpp"
#include "ito_connectivity/network_adapter.hpp"

#include <cassert>
#include <chrono>
#include <iostream>
#include <thread>

int main() {
    ito::connectivity::SessionConfig session{
        ito::connectivity::VenueIdentity{5, 1},
        1001,
        false
    };
    ito::connectivity::EndpointConnectorConfig endpoint{
        "127.0.0.1",
        12345,
        false,
        false
    };

    ito::connectivity::NetworkVenueAdapter adapter(session, endpoint);
    assert(adapter.status() == ito::connectivity::SessionStatus::Disabled);

    ito::connectivity::NormalizedOrder order{
        1, 100, 1001, 1, 7, 50, 100, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit
    };

    auto report = adapter.submit(order, 1000);
    assert(!report.has_value());

    adapter.disconnect(2000);
    assert(adapter.status() == ito::connectivity::SessionStatus::Disabled);

    return 0;
}
