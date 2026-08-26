#include "smart_order_router.hpp"

#include <algorithm>
#include <cstdlib>

namespace ito::routing {

SmartOrderRouter::SmartOrderRouter(session::SessionManager& sessions, RoutingPolicy policy) : sessions_(sessions), policy_(policy) {}

std::vector<RouteDecision> SmartOrderRouter::rank(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates) const {
    std::vector<RouteDecision> result;
    for (const auto& candidate : candidates) {
        if (!candidate.enabled || !candidate.authorized || !candidate.lease_valid || candidate.venue_id == 0 || candidate.broker_id == 0 || candidate.displayed_quantity < order.quantity || candidate.fee_bps > policy_.max_fee_bps || candidate.executable_price_ticks <= 0) {
            continue;
        }
        if (order.order_type == protocol::OrderType::Limit) {
            if (order.price_ticks <= 0) {
                continue;
            }
            const auto deviation = std::llabs(candidate.executable_price_ticks - order.price_ticks);
            if (deviation > policy_.max_price_deviation_ticks || (order.side == protocol::Side::Buy && candidate.executable_price_ticks > order.price_ticks) || (order.side == protocol::Side::Sell && candidate.executable_price_ticks < order.price_ticks)) {
                continue;
            }
        }
        result.push_back(RouteDecision{candidate.venue_id, candidate.broker_id, candidate.executable_price_ticks, candidate.fee_bps, candidate.rank});
    }
    std::stable_sort(result.begin(), result.end(), [this](const RouteDecision& left, const RouteDecision& right) {
        if (left.rank != right.rank) {
            return left.rank < right.rank;
        }
        if (left.fee_bps != right.fee_bps) {
            return left.fee_bps < right.fee_bps;
        }
        return left.venue_id < right.venue_id;
    });
    return result;
}

std::optional<RoutedExecution> SmartOrderRouter::submit(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates, std::uint64_t now_ns) {
    const auto routes = rank(order, candidates);
    for (const auto& route : routes) {
        const auto report = sessions_.submit(order, route.venue_id, now_ns);
        if (report.has_value() && report->status != connectivity::ExecutionStatus::Unknown && report->status != connectivity::ExecutionStatus::Rejected) {
            return RoutedExecution{route, *report};
        }
        if (!report.has_value()) {
            if (!policy_.allow_broker_fallback) {
                break;
            }
            continue;
        }
        if (report->status == connectivity::ExecutionStatus::Unknown || !policy_.allow_broker_fallback) {
            break;
        }
    }
    return std::nullopt;
}

}
