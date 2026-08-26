#pragma once

#include "endpoint_connector.hpp"
#include "venue_adapter.hpp"

#include <deque>
#include <memory>
#include <string>
#include <unordered_map>

namespace ito::connectivity {

class NetworkVenueAdapter final : public VenueAdapter {
public:
    NetworkVenueAdapter(SessionConfig session, EndpointConnectorConfig endpoint);
    VenueIdentity identity() const override;
    SessionStatus status() const override;
    bool connect(std::uint64_t now_ns) override;
    void disconnect(std::uint64_t now_ns) override;
    std::optional<ExecutionReport> submit(const NormalizedOrder& order, std::uint64_t now_ns) override;
    std::optional<ExecutionReport> cancel(std::uint64_t client_order_id, std::uint64_t now_ns) override;
    std::vector<ExecutionReport> poll(std::uint64_t now_ns) override;

private:
    SessionConfig session_;
    EndpointConnector connector_;
    SessionStatus status_{SessionStatus::Disabled};
    std::deque<ExecutionReport> reports_;
    std::unordered_map<std::uint64_t, NormalizedOrder> pending_;

    std::string encode_order(const NormalizedOrder& order) const;
    std::string encode_cancel(std::uint64_t client_order_id) const;
    void decode_reports(std::uint64_t now_ns);
};

}
