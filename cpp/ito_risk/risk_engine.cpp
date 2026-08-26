#include "risk_engine.hpp"

#include <limits>

namespace ito::risk {

namespace {
constexpr std::uint16_t kNotEnabled = 100;
constexpr std::uint16_t kExpiredLimits = 101;
constexpr std::uint16_t kUnhealthy = 102;
constexpr std::uint16_t kQuantity = 103;
constexpr std::uint16_t kNotional = 104;
constexpr std::uint16_t kPosition = 105;
constexpr std::uint16_t kRate = 106;
constexpr std::uint16_t kOverflow = 107;
constexpr std::uint16_t kInvalidOrder = 108;
constexpr std::uint16_t kInvalidLimits = 109;
}

RiskEngine::RiskEngine(core::EventJournal& journal) : journal_(journal) {}

void RiskEngine::set_limits(protocol::LimitSnapshot limits) {
    std::scoped_lock lock(mutex_);
    limits_ = limits;
    orders_this_second_ = 0;
    second_epoch_ns_ = 0;
}

void RiskEngine::set_position(protocol::PositionSnapshot position) {
    std::scoped_lock lock(mutex_);
    position_ = position;
}

void RiskEngine::set_health(Health health) {
    std::scoped_lock lock(mutex_);
    health_ = health;
}

bool RiskEngine::apply_fill(protocol::Side side, std::int64_t quantity) {
    std::scoped_lock lock(mutex_);
    if (quantity <= 0 || position_.gross_position < 0 || quantity > std::numeric_limits<std::int64_t>::max() - position_.gross_position) {
        return false;
    }
    const auto signed_quantity = side == protocol::Side::Buy ? quantity : -quantity;
    if (side != protocol::Side::Buy && side != protocol::Side::Sell) {
        return false;
    }
    if ((signed_quantity > 0 && position_.net_position > std::numeric_limits<std::int64_t>::max() - signed_quantity) || (signed_quantity < 0 && position_.net_position < std::numeric_limits<std::int64_t>::min() - signed_quantity)) {
        return false;
    }
    const auto next_gross = position_.gross_position + quantity;
    const auto next_net = position_.net_position + signed_quantity;
    if (next_gross > limits_.max_gross_position || next_net > limits_.max_net_position || next_net < -limits_.max_net_position) {
        return false;
    }
    position_.gross_position = next_gross;
    position_.net_position = next_net;
    journal_.append(protocol::EventType::Fill, 0, std::to_string(quantity));
    return true;
}

protocol::RiskDecision RiskEngine::reject(std::uint64_t correlation_id, std::uint64_t now_ns, std::uint16_t reason) {
    const protocol::RiskDecision decision{journal_.next_sequence(), correlation_id, limits_.version, protocol::RiskStatus::Rejected, reason, now_ns};
    journal_.append(protocol::EventType::RiskDecision, correlation_id, std::to_string(reason));
    return decision;
}

protocol::RiskDecision RiskEngine::evaluate(const protocol::OrderIntent& intent, std::uint64_t now_ns) {
    std::scoped_lock lock(mutex_);
    if (!limits_.trading_enabled) {
        return reject(intent.correlation_id, now_ns, kNotEnabled);
    }
    if (limits_.version == 0 || limits_.expires_ns == 0 || limits_.max_order_quantity <= 0 || limits_.max_order_notional_ticks <= 0 || limits_.max_net_position < 0 || limits_.max_gross_position < 0 || limits_.max_orders_per_second == 0) {
        return reject(intent.correlation_id, now_ns, kInvalidLimits);
    }
    if (limits_.expires_ns <= now_ns) {
        return reject(intent.correlation_id, now_ns, kExpiredLimits);
    }
    if (health_ != Health::Healthy) {
        return reject(intent.correlation_id, now_ns, kUnhealthy);
    }
    if (intent.event_id == 0 || intent.correlation_id == 0 || intent.strategy_id == 0 || intent.branch_id == 0 || intent.entity_id == 0 || intent.instrument_id == 0 || intent.venue_id == 0 || intent.account_id == 0 || intent.created_ns > now_ns || intent.order_type != protocol::OrderType::Limit || (intent.side != protocol::Side::Buy && intent.side != protocol::Side::Sell)) {
        return reject(intent.correlation_id, now_ns, kInvalidOrder);
    }
    if (intent.quantity <= 0 || intent.quantity > limits_.max_order_quantity) {
        return reject(intent.correlation_id, now_ns, kQuantity);
    }
    if (intent.price_ticks <= 0 || intent.price_ticks > std::numeric_limits<std::int64_t>::max() / intent.quantity) {
        return reject(intent.correlation_id, now_ns, kOverflow);
    }
    const auto notional = intent.price_ticks * intent.quantity;
    if (notional > limits_.max_order_notional_ticks) {
        return reject(intent.correlation_id, now_ns, kNotional);
    }
    const auto signed_quantity = intent.side == protocol::Side::Buy ? intent.quantity : -intent.quantity;
    if ((signed_quantity > 0 && (position_.net_position > limits_.max_net_position - signed_quantity || position_.net_position < std::numeric_limits<std::int64_t>::min() + signed_quantity)) || (signed_quantity < 0 && (position_.net_position < -limits_.max_net_position - signed_quantity || position_.net_position > std::numeric_limits<std::int64_t>::max() + signed_quantity))) {
        return reject(intent.correlation_id, now_ns, kPosition);
    }
    if (position_.gross_position < 0 || limits_.max_gross_position < position_.gross_position || intent.quantity > limits_.max_gross_position - position_.gross_position) {
        return reject(intent.correlation_id, now_ns, kPosition);
    }
    if (second_epoch_ns_ == 0 || now_ns < second_epoch_ns_ || now_ns - second_epoch_ns_ >= 1'000'000'000ULL) {
        second_epoch_ns_ = now_ns;
        orders_this_second_ = 0;
    }
    if (orders_this_second_ >= limits_.max_orders_per_second) {
        return reject(intent.correlation_id, now_ns, kRate);
    }
    ++orders_this_second_;
    const protocol::RiskDecision decision{journal_.next_sequence(), intent.correlation_id, limits_.version, protocol::RiskStatus::Approved, 0, now_ns};
    journal_.append(protocol::EventType::RiskDecision, intent.correlation_id, "approved");
    return decision;
}

protocol::PositionSnapshot RiskEngine::position() const {
    std::scoped_lock lock(mutex_);
    return position_;
}

protocol::LimitSnapshot RiskEngine::limits() const {
    std::scoped_lock lock(mutex_);
    return limits_;
}

}
