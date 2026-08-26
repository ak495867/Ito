#pragma once

#include <cstdint>
#include <string>

namespace ito::protocol {

enum class Side : std::uint8_t { Buy = 1, Sell = 2 };
enum class OrderType : std::uint8_t { Limit = 1, Market = 2 };
enum class TimeInForce : std::uint8_t { Day = 1, IOC = 2, FOK = 3 };
enum class RiskStatus : std::uint8_t { Approved = 1, Rejected = 2, Halted = 3 };
enum class EventType : std::uint8_t { Intent = 1, RiskDecision = 2, OrderSent = 3, Acknowledgment = 4, Fill = 5, Cancel = 6, Halt = 7 };

struct OrderIntent {
    std::uint64_t event_id{};
    std::uint64_t correlation_id{};
    std::uint64_t strategy_id{};
    std::uint64_t branch_id{};
    std::uint64_t entity_id{};
    std::uint32_t instrument_id{};
    std::uint16_t venue_id{};
    std::uint32_t account_id{};
    Side side{Side::Buy};
    OrderType order_type{OrderType::Limit};
    TimeInForce time_in_force{TimeInForce::Day};
    std::int64_t price_ticks{};
    std::int64_t quantity{};
    std::uint64_t created_ns{};
};

struct LimitSnapshot {
    std::uint64_t version{};
    std::uint64_t expires_ns{};
    std::int64_t max_order_quantity{};
    std::int64_t max_order_notional_ticks{};
    std::int64_t max_net_position{};
    std::int64_t max_gross_position{};
    std::uint64_t max_orders_per_second{};
    bool trading_enabled{};
};

struct RiskDecision {
    std::uint64_t event_id{};
    std::uint64_t correlation_id{};
    std::uint64_t limit_version{};
    RiskStatus status{RiskStatus::Rejected};
    std::uint16_t reason_code{};
    std::uint64_t decided_ns{};
};

struct ExecutionEvent {
    std::uint64_t event_id{};
    std::uint64_t correlation_id{};
    std::uint64_t venue_order_id{};
    EventType type{EventType::Intent};
    std::int64_t price_ticks{};
    std::int64_t quantity{};
    std::uint64_t timestamp_ns{};
};

struct PositionSnapshot {
    std::int64_t net_position{};
    std::int64_t gross_position{};
};

struct EventEnvelope {
    std::uint64_t event_id{};
    std::uint64_t sequence{};
    EventType type{EventType::Intent};
    std::string payload;
};

}
