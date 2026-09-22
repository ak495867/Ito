#pragma once

#include "../ito_risk/risk_engine.hpp"

#include <cstdint>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <vector>

namespace ito::execution {

enum class GatewayState : std::uint8_t { Disconnected = 1, Ready = 2, Halted = 3, Uncertain = 4 };
enum class CircuitState : std::uint8_t { Closed = 1, HalfOpen = 2, Open = 3 };

class ExecutionEngine {
public:
    ExecutionEngine(core::EventJournal& journal, risk::RiskEngine& risk_engine);
    void set_gateway_state(GatewayState state);
    void set_halted(bool halted);
    std::optional<protocol::ExecutionEvent> submit(const protocol::OrderIntent& intent, std::uint64_t now_ns);
    bool acknowledge(std::uint64_t correlation_id, std::uint64_t venue_order_id, std::uint64_t now_ns);
    std::vector<protocol::ExecutionEvent> events() const;
    CircuitState circuit_state() const;

private:
    core::EventJournal& journal_;
    risk::RiskEngine& risk_engine_;
    mutable std::mutex mutex_;
    GatewayState gateway_state_{GatewayState::Disconnected};
    CircuitState circuit_state_{CircuitState::Closed};
    bool halted_{true};
    std::uint64_t next_venue_order_id_{1};
    std::uint64_t circuit_failures_{0};
    std::uint64_t circuit_opened_at_ns_{0};
    bool half_open_in_flight_{false};
    std::unordered_map<std::uint64_t, protocol::ExecutionEvent> active_;
};

}