#include "network_adapter.hpp"

#include <sstream>
#include <utility>

namespace ito::connectivity {

namespace {
std::string side_name(protocol::Side side) {
    return side == protocol::Side::Buy ? "B" : "S";
}
}

NetworkVenueAdapter::NetworkVenueAdapter(SessionConfig session, EndpointConnectorConfig endpoint)
    : session_(std::move(session)), connector_(std::move(endpoint)) {}

VenueIdentity NetworkVenueAdapter::identity() const {
    return session_.venue;
}

SessionStatus NetworkVenueAdapter::status() const {
    return status_;
}

bool NetworkVenueAdapter::connect(std::uint64_t now_ns) {
    static_cast<void>(now_ns);
    if (!session_.live_enabled) {
        status_ = SessionStatus::Disabled;
        return false;
    }
    status_ = SessionStatus::Connecting;
    if (!connector_.open()) {
        status_ = SessionStatus::Degraded;
        return false;
    }
    status_ = SessionStatus::Ready;
    return true;
}

void NetworkVenueAdapter::disconnect(std::uint64_t now_ns) {
    static_cast<void>(now_ns);
    connector_.close();
    status_ = SessionStatus::Disabled;
}

std::string NetworkVenueAdapter::encode_order(const NormalizedOrder& order) const {
    std::ostringstream output;
    output << "N|" << order.client_order_id << "|" << order.instrument_id << "|" << side_name(order.side) << "|" << order.price_ticks << "|" << order.quantity << "|" << order.strategy_id << '\n';
    return output.str();
}

std::string NetworkVenueAdapter::encode_cancel(std::uint64_t client_order_id) const {
    return "C|" + std::to_string(client_order_id) + "\n";
}

std::optional<ExecutionReport> NetworkVenueAdapter::submit(const NormalizedOrder& order, std::uint64_t now_ns) {
    if (order.client_order_id == 0 || order.correlation_id == 0 || order.quantity <= 0 || status_ != SessionStatus::Ready || pending_.contains(order.client_order_id)) {
        return std::nullopt;
    }
    if (!connector_.send(encode_order(order))) {
        status_ = SessionStatus::Degraded;
        return std::nullopt;
    }
    pending_.emplace(order.client_order_id, order);
    status_ = SessionStatus::Uncertain;
    return ExecutionReport{order.correlation_id, order.client_order_id, 0, 0, ExecutionStatus::Unknown, order.price_ticks, 0, order.quantity, now_ns, now_ns, 0};
}

std::optional<ExecutionReport> NetworkVenueAdapter::cancel(std::uint64_t client_order_id, std::uint64_t now_ns) {
    if (client_order_id == 0 || status_ == SessionStatus::Disabled || status_ == SessionStatus::Degraded || !pending_.contains(client_order_id) || !connector_.send(encode_cancel(client_order_id))) {
        status_ = SessionStatus::Uncertain;
        return std::nullopt;
    }
    status_ = SessionStatus::Uncertain;
    return ExecutionReport{pending_.at(client_order_id).correlation_id, client_order_id, 0, 0, ExecutionStatus::Unknown, 0, 0, pending_.at(client_order_id).quantity, now_ns, now_ns, 0};
}

void NetworkVenueAdapter::decode_reports(std::uint64_t now_ns) {
    const auto raw = connector_.receive();
    if (!raw.has_value()) {
        return;
    }
    std::istringstream input(*raw);
    std::string line;
    while (std::getline(input, line, '\n')) {
        std::istringstream fields(line);
        std::string kind;
        std::string client;
        std::getline(fields, kind, '|');
        std::getline(fields, client, '|');
        try {
            const auto client_order_id = std::stoull(client);
            const auto pending = pending_.find(client_order_id);
            const auto correlation_id = pending == pending_.end() ? 0 : pending->second.correlation_id;
            if (kind == "ACK") {
                status_ = SessionStatus::Ready;
                std::string venue;
                std::getline(fields, venue, '|');
                reports_.push_back(ExecutionReport{correlation_id, client_order_id, std::stoull(venue), 0, ExecutionStatus::Accepted, 0, 0, pending == pending_.end() ? 0 : pending->second.quantity, now_ns, now_ns, 0});
            } else if (kind == "FILL") {
                status_ = SessionStatus::Ready;
                std::string execution;
                std::string price;
                std::string quantity;
                std::string leaves;
                std::getline(fields, execution, '|');
                std::getline(fields, price, '|');
                std::getline(fields, quantity, '|');
                std::getline(fields, leaves, '|');
                const auto remaining = std::stoll(leaves);
                reports_.push_back(ExecutionReport{correlation_id, client_order_id, 0, std::stoull(execution), remaining == 0 ? ExecutionStatus::Filled : ExecutionStatus::PartiallyFilled, std::stoll(price), std::stoll(quantity), remaining, now_ns, now_ns, 0});
                if (remaining == 0) {
                    pending_.erase(client_order_id);
                }
            } else if (kind == "REJECT") {
                status_ = SessionStatus::Ready;
                reports_.push_back(ExecutionReport{correlation_id, client_order_id, 0, 0, ExecutionStatus::Rejected, 0, 0, 0, now_ns, now_ns, 400});
                pending_.erase(client_order_id);
            }
        } catch (...) {
            reports_.push_back(ExecutionReport{0, 0, 0, 0, ExecutionStatus::Unknown, 0, 0, 0, now_ns, now_ns, 401});
        }
    }
}

std::vector<ExecutionReport> NetworkVenueAdapter::poll(std::uint64_t now_ns) {
    decode_reports(now_ns);
    std::vector<ExecutionReport> result(reports_.begin(), reports_.end());
    reports_.clear();
    if (pending_.empty() && status_ == SessionStatus::Uncertain) {
        status_ = SessionStatus::Ready;
    }
    return result;
}

}
