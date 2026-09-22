#include "execution_engine.hpp"

#include <string>

namespace ito::execution {

namespace {
constexpr std::uint16_t kGatewayUnavailable = 200;
constexpr std::uint16_t kHalted = 201;
constexpr std::uint16_t kRiskRejected = 202;
constexpr std::uint16_t kDuplicateCorrelation = 203;
constexpr std::uint16_t kCircuitOpen = 204;
constexpr std::uint16_t kCircuitHalfOpen = 205;
constexpr std::uint64_t kCircuitFailureThreshold = 5;
constexpr std::uint64_t kCircuitCooldownNs = 30'000'000'000ULL;
}

ExecutionEngine::ExecutionEngine(core::EventJournal& journal, risk::RiskEngine& risk_engine)
    : journal_(journal), risk_engine_(risk_engine) {}

void ExecutionEngine::set_gateway_state(GatewayState state) {
    std::scoped_lock lock(mutex_);
    gateway_state_ = state;
    if (state == GatewayState::Ready) {
        circuit_state_ = CircuitState::Closed;
        circuit_failures_ = 0;
        circuit_opened_at_ns_ = 0;
    }
}

void ExecutionEngine::set_halted(bool halted) {
    std::scoped_lock lock(mutex_);
    halted_ = halted;
    if (halted_) {
        gateway_state_ = GatewayState::Halted;
        journal_.append(protocol::EventType::Halt, 0, "halted");
    } else if (gateway_state_ == GatewayState::Halted) {
        gateway_state_ = GatewayState::Ready;
        journal_.append(protocol::EventType::Acknowledgment, 0, "halt_cleared");
    }
}

std::optional<protocol::ExecutionEvent> ExecutionEngine::submit(const protocol::OrderIntent& intent, std::uint64_t now_ns) {
    std::scoped_lock lock(mutex_);
    if (intent.correlation_id == 0 || active_.contains(intent.correlation_id)) {
        journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(kDuplicateCorrelation));
        return std::nullopt;
    }
    if (circuit_state_ == CircuitState::Open) {
        if (now_ns - circuit_opened_at_ns_ >= kCircuitCooldownNs) {
            circuit_state_ = CircuitState::HalfOpen;
        } else {
            journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(kCircuitOpen));
            return std::nullopt;
        }
    }
    if (circuit_state_ == CircuitState::HalfOpen && half_open_in_flight_) {
        journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(kCircuitHalfOpen));
        return std::nullopt;
    }
    if (halted_ || gateway_state_ != GatewayState::Ready) {
        circuit_failures_++;
        if (circuit_failures_ >= kCircuitFailureThreshold) {
            circuit_state_ = CircuitState::Open;
            circuit_opened_at_ns_ = now_ns;
        }
        journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(kGatewayUnavailable));
        return std::nullopt;
    }
    const auto decision = risk_engine_.evaluate(intent, now_ns);
    if (decision.status != protocol::RiskStatus::Approved) {
        circuit_failures_++;
        if (circuit_failures_ >= kCircuitFailureThreshold) {
            circuit_state_ = CircuitState::Open;
            circuit_opened_at_ns_ = now_ns;
        }
        journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(kRiskRejected));
        return std::nullopt;
    }
    if (circuit_state_ == CircuitState::HalfOpen) {
        half_open_in_flight_ = true;
    }
    protocol::ExecutionEvent event{0, intent.correlation_id, next_venue_order_id_++, protocol::EventType::OrderSent, intent.price_ticks, intent.quantity, now_ns};
    event.event_id = journal_.append(protocol::EventType::OrderSent, intent.correlation_id, std::to_string(event.venue_order_id));
    active_.emplace(intent.correlation_id, event);
    return event;
}

bool ExecutionEngine::acknowledge(std::uint64_t correlation_id, std::uint64_t venue_order_id, std::uint64_t now_ns) {
    std::scoped_lock lock(mutex_);
    const auto it = active_.find(correlation_id);
    if (it == active_.end() || it->second.venue_order_id != venue_order_id) {
        gateway_state_ = GatewayState::Uncertain;
        circuit_failures_++;
        if (circuit_failures_ >= kCircuitFailureThreshold) {
            circuit_state_ = CircuitState::Open;
            circuit_opened_at_ns_ = now_ns;
        }
        journal_.append(protocol::EventType::Acknowledgment, correlation_id, "uncertain");
        return false;
    }
    it->second.type = protocol::EventType::Acknowledgment;
    it->second.timestamp_ns = now_ns;
    journal_.append(protocol::EventType::Acknowledgment, correlation_id, std::to_string(venue_order_id));
    if (circuit_state_ == CircuitState::HalfOpen) {
        circuit_state_ = CircuitState::Closed;
        circuit_failures_ = 0;
        circuit_opened_at_ns_ = 0;
        half_open_in_flight_ = false;
    }
    active_.erase(it);
    return true;
}

std::vector<protocol::ExecutionEvent> ExecutionEngine::events() const {
    std::scoped_lock lock(mutex_);
    std::vector<protocol::ExecutionEvent> result;
    result.reserve(active_.size());
    for (const auto& [key, value] : active_) {
        static_cast<void>(key);
        result.push_back(value);
    }
    return result;
}

CircuitState ExecutionEngine::circuit_state() const {
    std::scoped_lock lock(mutex_);
    return circuit_state_;
}

}