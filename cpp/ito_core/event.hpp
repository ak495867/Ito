#pragma once

#include "../../interfaces/schemas/ito_protocol.hpp"

#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

namespace ito::core {

class EventJournal {
public:
    std::uint64_t append(protocol::EventType type, std::uint64_t correlation_id, std::string payload);
    std::vector<protocol::EventEnvelope> snapshot() const;
    std::uint64_t next_sequence() const;

private:
    mutable std::mutex mutex_;
    std::uint64_t next_sequence_{1};
    std::uint64_t next_event_id_{1};
    std::vector<protocol::EventEnvelope> events_;
};

}
