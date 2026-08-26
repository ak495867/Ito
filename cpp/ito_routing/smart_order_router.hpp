#pragma once

#include "../ito_connectivity/venue_types.hpp"
#include "../ito_session/session_manager.hpp"

#include <cstdint>
#include <optional>
#include <vector>

namespace ito::routing {

struct RouteCandidate {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    std::int64_t executable_price_ticks{};
    std::int64_t displayed_quantity{};
    std::uint32_t fee_bps{};
    std::uint32_t rank{};
    bool enabled{};
    bool authorized{};
    bool lease_valid{};
};

struct RoutingPolicy {
    std::uint32_t max_fee_bps{100};
    std::int64_t max_price_deviation_ticks{500};
    bool allow_broker_fallback{true};
};

struct RouteDecision {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    std::int64_t price_ticks{};
    std::uint32_t fee_bps{};
    std::uint32_t rank{};
};

struct RoutedExecution {
    RouteDecision route;
    connectivity::ExecutionReport report;
};

class SmartOrderRouter {
public:
    SmartOrderRouter(session::SessionManager& sessions, RoutingPolicy policy);
    std::vector<RouteDecision> rank(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates) const;
    std::optional<RoutedExecution> submit(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates, std::uint64_t now_ns);

private:
    session::SessionManager& sessions_;
    RoutingPolicy policy_;
};

}
