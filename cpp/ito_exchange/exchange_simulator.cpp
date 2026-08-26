#include "exchange_simulator.hpp"

#include <algorithm>
#include <string>

namespace ito::exchange {

namespace {
constexpr std::uint16_t kInvalidOrder = 300;
constexpr std::uint16_t kUnsupportedFok = 301;
}

ExchangeSimulator::ExchangeSimulator(core::EventJournal& journal) : next_order_id_(1), journal_(journal) {}

void ExchangeSimulator::rest(const RestingOrder& order) {
    if (order.side == protocol::Side::Buy) {
        bids_[order.price_ticks].push_back(order);
    } else {
        asks_[order.price_ticks].push_back(order);
    }
    index_[order.venue_order_id] = order;
}

void ExchangeSimulator::remove_from_index(std::uint64_t venue_order_id) {
    index_.erase(venue_order_id);
}

SubmitResult ExchangeSimulator::submit(const protocol::OrderIntent& intent, std::uint64_t timestamp_ns) {
    const auto order_id = next_order_id_++;
    SubmitResult result{order_id, intent.quantity, {}, false};
    if (intent.quantity <= 0 || intent.price_ticks <= 0) {
        journal_.append(protocol::EventType::Acknowledgment, intent.correlation_id, std::to_string(kInvalidOrder));
        return result;
    }
    if (intent.time_in_force == protocol::TimeInForce::FOK) {
        journal_.append(protocol::EventType::Acknowledgment, intent.correlation_id, std::to_string(kUnsupportedFok));
        return result;
    }
    result = intent.side == protocol::Side::Buy ? match_buy(intent, order_id, timestamp_ns) : match_sell(intent, order_id, timestamp_ns);
    result.accepted = true;
    journal_.append(protocol::EventType::Acknowledgment, intent.correlation_id, std::to_string(order_id));
    for (const auto& match : result.matches) {
        journal_.append(protocol::EventType::Fill, intent.correlation_id, std::to_string(match.maker_order_id) + ":" + std::to_string(match.quantity) + ":" + std::to_string(match.price_ticks));
    }
    return result;
}

SubmitResult ExchangeSimulator::match_buy(const protocol::OrderIntent& intent, std::uint64_t order_id, std::uint64_t timestamp_ns) {
    SubmitResult result{order_id, intent.quantity, {}, true};
    while (result.remaining_quantity > 0 && !asks_.empty()) {
        auto level_it = asks_.begin();
        if (intent.order_type == protocol::OrderType::Limit && intent.price_ticks < level_it->first) {
            break;
        }
        auto& level = level_it->second;
        auto& maker = level.front();
        const auto traded = std::min(result.remaining_quantity, maker.remaining_quantity);
        result.matches.push_back(MatchEvent{order_id, maker.venue_order_id, maker.price_ticks, traded, timestamp_ns});
        result.remaining_quantity -= traded;
        maker.remaining_quantity -= traded;
        index_[maker.venue_order_id].remaining_quantity = maker.remaining_quantity;
        if (maker.remaining_quantity == 0) {
            remove_from_index(maker.venue_order_id);
            level.pop_front();
        }
        if (level.empty()) {
            asks_.erase(level_it);
        }
    }
    if (result.remaining_quantity > 0 && intent.time_in_force == protocol::TimeInForce::Day) {
        rest(RestingOrder{order_id, intent.correlation_id, intent.side, intent.price_ticks, result.remaining_quantity, order_id});
    }
    return result;
}

SubmitResult ExchangeSimulator::match_sell(const protocol::OrderIntent& intent, std::uint64_t order_id, std::uint64_t timestamp_ns) {
    SubmitResult result{order_id, intent.quantity, {}, true};
    while (result.remaining_quantity > 0 && !bids_.empty()) {
        auto level_it = bids_.begin();
        if (intent.order_type == protocol::OrderType::Limit && intent.price_ticks > level_it->first) {
            break;
        }
        auto& level = level_it->second;
        auto& maker = level.front();
        const auto traded = std::min(result.remaining_quantity, maker.remaining_quantity);
        result.matches.push_back(MatchEvent{order_id, maker.venue_order_id, maker.price_ticks, traded, timestamp_ns});
        result.remaining_quantity -= traded;
        maker.remaining_quantity -= traded;
        index_[maker.venue_order_id].remaining_quantity = maker.remaining_quantity;
        if (maker.remaining_quantity == 0) {
            remove_from_index(maker.venue_order_id);
            level.pop_front();
        }
        if (level.empty()) {
            bids_.erase(level_it);
        }
    }
    if (result.remaining_quantity > 0 && intent.time_in_force == protocol::TimeInForce::Day) {
        rest(RestingOrder{order_id, intent.correlation_id, intent.side, intent.price_ticks, result.remaining_quantity, order_id});
    }
    return result;
}

bool ExchangeSimulator::cancel(std::uint64_t venue_order_id, std::uint64_t timestamp_ns) {
    const auto found = index_.find(venue_order_id);
    if (found == index_.end()) {
        return false;
    }
    const auto order = found->second;
    if (order.side == protocol::Side::Buy) {
        auto level_it = bids_.find(order.price_ticks);
        if (level_it != bids_.end()) {
            auto& level = level_it->second;
            level.erase(std::remove_if(level.begin(), level.end(), [venue_order_id](const RestingOrder& value) { return value.venue_order_id == venue_order_id; }), level.end());
            if (level.empty()) {
                bids_.erase(level_it);
            }
        }
    } else {
        auto level_it = asks_.find(order.price_ticks);
        if (level_it != asks_.end()) {
            auto& level = level_it->second;
            level.erase(std::remove_if(level.begin(), level.end(), [venue_order_id](const RestingOrder& value) { return value.venue_order_id == venue_order_id; }), level.end());
            if (level.empty()) {
                asks_.erase(level_it);
            }
        }
    }
    remove_from_index(venue_order_id);
    journal_.append(protocol::EventType::Cancel, order.correlation_id, std::to_string(venue_order_id) + ":" + std::to_string(timestamp_ns));
    return true;
}

std::optional<RestingOrder> ExchangeSimulator::find(std::uint64_t venue_order_id) const {
    const auto found = index_.find(venue_order_id);
    if (found == index_.end()) {
        return std::nullopt;
    }
    return found->second;
}

std::int64_t ExchangeSimulator::best_bid() const {
    return bids_.empty() ? 0 : bids_.begin()->first;
}

std::int64_t ExchangeSimulator::best_ask() const {
    return asks_.empty() ? 0 : asks_.begin()->first;
}

std::size_t ExchangeSimulator::resting_count() const {
    return index_.size();
}

}
