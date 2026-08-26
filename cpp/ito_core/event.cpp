#include "event.hpp"

#include <utility>

namespace ito::core {

std::uint64_t EventJournal::append(protocol::EventType type, std::uint64_t correlation_id, std::string payload) {
    std::scoped_lock lock(mutex_);
    const auto event_id = next_event_id_++;
    payload = std::to_string(correlation_id) + ":" + std::move(payload);
    events_.push_back(protocol::EventEnvelope{event_id, next_sequence_++, type, std::move(payload)});
    return event_id;
}

std::vector<protocol::EventEnvelope> EventJournal::snapshot() const {
    std::scoped_lock lock(mutex_);
    return events_;
}

std::uint64_t EventJournal::next_sequence() const {
    std::scoped_lock lock(mutex_);
    return next_sequence_;
}

}
