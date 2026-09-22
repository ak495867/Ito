#pragma once

#include "../../interfaces/schemas/ito_protocol.hpp"

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace ito::reference {

class EventSink {
public:
    virtual ~EventSink() = default;
    virtual void on_event(const protocol::EventEnvelope& event) = 0;
    virtual void on_error(std::uint64_t correlation_id, std::uint16_t error_code, std::string_view message) = 0;
};

class EventSource {
public:
    virtual ~EventSource() = default;
    virtual void subscribe(std::shared_ptr<EventSink> sink) = 0;
    virtual void unsubscribe(std::shared_ptr<EventSink> sink) = 0;
};

class EventJournal {
public:
    virtual ~EventJournal() = default;
    virtual std::uint64_t append(protocol::EventType type, std::uint64_t correlation_id, std::string_view payload) = 0;
    virtual std::vector<protocol::EventEnvelope> snapshot(std::uint64_t from_sequence = 0) const = 0;
    virtual std::uint64_t next_sequence() const = 0;
    virtual std::uint64_t next_event_id() const = 0;
};

class EventReplay {
public:
    virtual ~EventReplay() = default;
    virtual std::vector<protocol::EventEnvelope> replay(std::uint64_t from_sequence, std::uint64_t count) const = 0;
    virtual std::optional<std::uint64_t> last_valid_sequence() const = 0;
};

struct EventHandler {
    std::function<void(const protocol::EventEnvelope&)> on_intent;
    std::function<void(const protocol::EventEnvelope&)> on_risk_decision;
    std::function<void(const protocol::EventEnvelope&)> on_order_sent;
    std::function<void(const protocol::EventEnvelope&)> on_acknowledgment;
    std::function<void(const protocol::EventEnvelope&)> on_fill;
    std::function<void(const protocol::EventEnvelope&)> on_cancel;
    std::function<void(const protocol::EventEnvelope&)> on_halt;
};

inline void dispatch_event(const protocol::EventEnvelope& event, const EventHandler& handler) {
    switch (event.type) {
        case protocol::EventType::Intent:
            if (handler.on_intent) handler.on_intent(event);
            break;
        case protocol::EventType::RiskDecision:
            if (handler.on_risk_decision) handler.on_risk_decision(event);
            break;
        case protocol::EventType::OrderSent:
            if (handler.on_order_sent) handler.on_order_sent(event);
            break;
        case protocol::EventType::Acknowledgment:
            if (handler.on_acknowledgment) handler.on_acknowledgment(event);
            break;
        case protocol::EventType::Fill:
            if (handler.on_fill) handler.on_fill(event);
            break;
        case protocol::EventType::Cancel:
            if (handler.on_cancel) handler.on_cancel(event);
            break;
        case protocol::EventType::Halt:
            if (handler.on_halt) handler.on_halt(event);
            break;
    }
}

}