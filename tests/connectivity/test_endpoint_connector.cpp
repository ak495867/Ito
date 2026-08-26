#include "ito_connectivity/endpoint_connector.hpp"

#include <cassert>

int main() {
    ito::connectivity::EndpointConnector disabled({"127.0.0.1", 1, true, false, "", "", ""});
    assert(!disabled.open());
    assert(!disabled.connected());
    assert(!disabled.send("probe"));
    assert(!disabled.receive().has_value());

    ito::connectivity::EndpointConnector incomplete_mtls({"127.0.0.1", 1, true, false, "/tmp/ca.pem", "/tmp/client.pem", ""});
    assert(!incomplete_mtls.open());
    assert(!incomplete_mtls.connected());

    ito::connectivity::EndpointConnector disabled_plain({"127.0.0.1", 1, false, false, "", "", ""});
    assert(!disabled_plain.open());
    assert(!disabled_plain.connected());
    return 0;
}
