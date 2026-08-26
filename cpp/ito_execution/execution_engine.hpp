#pragma once

#include "../ito_risk/risk_engine.hpp"

#include <cstdint>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <vector>

namespace ito::execution {

enum class GatewayState : std::uint8_t { Disconnected = 1, Ready = 2, Halted = 3, Uncertain = 4 };

class ExecutionEngine {
public:
    ExecutionEngine(core::EventJournal& journal, risk::RiskEngine& risk_engine);
    void set_gateway_state(GatewayState state);
    void set_halted(bool halted);
    std::optional<protocol::ExecutionEvent> submit(const protocol::OrderIntent& intent, std::uint64_t now_ns);
    bool acknowledge(std::uint64_t correlation_id, std::uint64_t venue_order_id, std::uint64_t now_ns);
    std::vector<protocol::ExecutionEvent> events() const;

private:
    core::EventJournal& journal_;
    risk::RiskEngine& risk_engine_;
    mutable std::mutex mutex_;
    GatewayState gateway_state_{GatewayState::Disconnected};
    bool halted_{true};
    std::uint64_t next_venue_order_id_{1};
    std::unordered_map<std::uint64_t, protocol::ExecutionEvent> active_;
};

}
