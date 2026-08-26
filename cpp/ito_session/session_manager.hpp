#pragma once

#include "../ito_connectivity/venue_adapter.hpp"

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <vector>

namespace ito::session {

struct SessionStatusView {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    connectivity::SessionStatus status{connectivity::SessionStatus::Disabled};
    std::uint64_t last_transition_ns{};
};

class SessionManager {
public:
    bool add(std::unique_ptr<connectivity::VenueAdapter> adapter, std::uint64_t now_ns);
    bool connect(std::uint16_t venue_id, std::uint64_t now_ns);
    bool disconnect(std::uint16_t venue_id, std::uint64_t now_ns);
    std::optional<connectivity::ExecutionReport> submit(const connectivity::NormalizedOrder& order, std::uint16_t venue_id, std::uint64_t now_ns);
    std::optional<connectivity::ExecutionReport> cancel(std::uint64_t client_order_id, std::uint16_t venue_id, std::uint64_t now_ns);
    std::vector<SessionStatusView> statuses() const;
    std::vector<connectivity::ExecutionReport> poll_all(std::uint64_t now_ns);

private:
    struct Entry {
        std::unique_ptr<connectivity::VenueAdapter> adapter;
        std::uint64_t last_transition_ns{};
    };
    std::map<std::uint16_t, Entry> sessions_;
};

}
