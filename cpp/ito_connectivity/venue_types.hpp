#pragma once

#include "../../interfaces/schemas/ito_protocol.hpp"

#include <cstdint>
#include <string>

namespace ito::connectivity {

enum class VenueKind : std::uint8_t { Exchange = 1, Broker = 2, DarkPool = 3, Simulator = 4 };
enum class SessionStatus : std::uint8_t { Disabled = 1, Connecting = 2, Ready = 3, Degraded = 4, Halted = 5, Uncertain = 6 };
enum class ExecutionStatus : std::uint8_t { Accepted = 1, Rejected = 2, PartiallyFilled = 3, Filled = 4, Cancelled = 5, Expired = 6, Unknown = 7 };

enum class AdapterProtocol : std::uint8_t { Fix = 1, Binary = 2, Rest = 3, WebSocket = 4, Simulator = 5 };

struct VenueIdentity {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    VenueKind kind{VenueKind::Simulator};
    AdapterProtocol protocol{AdapterProtocol::Simulator};
    std::string name;
    std::string region;
};

struct SessionConfig {
    std::uint64_t branch_id{};
    VenueIdentity venue;
    std::string session_name;
    std::string endpoint;
    std::uint64_t heartbeat_ms{1000};
    std::uint64_t reconnect_backoff_ms{100};
    std::uint64_t max_messages_per_second{1000};
    bool live_enabled{false};
};

struct NormalizedOrder {
    std::uint64_t correlation_id{};
    std::uint64_t client_order_id{};
    std::uint32_t instrument_id{};
    std::uint32_t account_id{};
    protocol::Side side{protocol::Side::Buy};
    protocol::OrderType order_type{protocol::OrderType::Limit};
    protocol::TimeInForce time_in_force{protocol::TimeInForce::Day};
    std::int64_t price_ticks{};
    std::int64_t quantity{};
    std::uint64_t strategy_id{};
};

struct ExecutionReport {
    std::uint64_t correlation_id{};
    std::uint64_t client_order_id{};
    std::uint64_t venue_order_id{};
    std::uint64_t execution_id{};
    ExecutionStatus status{ExecutionStatus::Unknown};
    std::int64_t price_ticks{};
    std::int64_t quantity{};
    std::int64_t leaves_quantity{};
    std::uint64_t exchange_timestamp_ns{};
    std::uint64_t receive_timestamp_ns{};
    std::uint16_t reason_code{};
};

struct MarketEvent {
    std::uint16_t venue_id{};
    std::uint32_t instrument_id{};
    std::int64_t bid_ticks{};
    std::int64_t ask_ticks{};
    std::int64_t bid_quantity{};
    std::int64_t ask_quantity{};
    std::uint64_t venue_sequence{};
    std::uint64_t exchange_timestamp_ns{};
    std::uint64_t receive_timestamp_ns{};
};

}
