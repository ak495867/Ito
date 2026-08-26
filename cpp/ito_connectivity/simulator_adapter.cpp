#include "simulator_adapter.hpp"

namespace ito::connectivity {

SimulatorAdapter::SimulatorAdapter(core::EventJournal& journal, VenueIdentity identity)
    : journal_(journal), identity_(std::move(identity)), exchange_(journal) {}

VenueIdentity SimulatorAdapter::identity() const {
    return identity_;
}

SessionStatus SimulatorAdapter::status() const {
    return status_;
}

bool SimulatorAdapter::connect(std::uint64_t now_ns) {
    static_cast<void>(now_ns);
    status_ = SessionStatus::Ready;
    return true;
}

void SimulatorAdapter::disconnect(std::uint64_t now_ns) {
    static_cast<void>(now_ns);
    status_ = SessionStatus::Disabled;
}

std::optional<ExecutionReport> SimulatorAdapter::submit(const NormalizedOrder& order, std::uint64_t now_ns) {
    if (status_ != SessionStatus::Ready || !identity_.venue_id) {
        return std::nullopt;
    }
    const protocol::OrderIntent intent{order.client_order_id, order.correlation_id, order.strategy_id, 0, 0, order.instrument_id, identity_.venue_id, order.account_id, order.side, order.order_type, order.time_in_force, order.price_ticks, order.quantity, now_ns};
    const auto result = exchange_.submit(intent, now_ns);
    if (!result.accepted) {
        return ExecutionReport{order.correlation_id, order.client_order_id, result.venue_order_id, 0, ExecutionStatus::Rejected, order.price_ticks, 0, order.quantity, now_ns, now_ns, 300};
    }
    std::int64_t filled = 0;
    for (const auto& match : result.matches) {
        filled += match.quantity;
        journal_.append(protocol::EventType::Fill, order.correlation_id, std::to_string(match.maker_order_id) + ":" + std::to_string(match.quantity));
    }
    const auto status = filled == 0 ? ExecutionStatus::Accepted : (result.remaining_quantity == 0 ? ExecutionStatus::Filled : ExecutionStatus::PartiallyFilled);
    if (result.remaining_quantity > 0) {
        client_to_venue_[order.client_order_id] = result.venue_order_id;
    }
    return ExecutionReport{order.correlation_id, order.client_order_id, result.venue_order_id, next_execution_id_++, status, order.price_ticks, filled, result.remaining_quantity, now_ns, now_ns, 0};
}

std::optional<ExecutionReport> SimulatorAdapter::cancel(std::uint64_t client_order_id, std::uint64_t now_ns) {
    if (status_ != SessionStatus::Ready) {
        return std::nullopt;
    }
    const auto found = client_to_venue_.find(client_order_id);
    if (found == client_to_venue_.end()) {
        return ExecutionReport{0, client_order_id, 0, 0, ExecutionStatus::Unknown, 0, 0, 0, now_ns, now_ns, 304};
    }
    const auto venue_order_id = found->second;
    const auto cancelled = exchange_.cancel(venue_order_id, now_ns);
    if (!cancelled) {
        return ExecutionReport{0, client_order_id, venue_order_id, 0, ExecutionStatus::Unknown, 0, 0, 0, now_ns, now_ns, 304};
    }
    client_to_venue_.erase(found);
    return ExecutionReport{0, client_order_id, venue_order_id, 0, ExecutionStatus::Cancelled, 0, 0, 0, now_ns, now_ns, 0};
}

std::vector<ExecutionReport> SimulatorAdapter::poll(std::uint64_t now_ns) {
    static_cast<void>(now_ns);
    return {};
}

}
