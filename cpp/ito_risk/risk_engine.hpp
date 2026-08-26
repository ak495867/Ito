#pragma once

#include "../ito_core/event.hpp"

#include <cstdint>
#include <mutex>

namespace ito::risk {

enum class Health : std::uint8_t { Healthy = 1, Stale = 2, Halted = 3 };

class RiskEngine {
public:
    explicit RiskEngine(core::EventJournal& journal);
    void set_limits(protocol::LimitSnapshot limits);
    void set_position(protocol::PositionSnapshot position);
    void set_health(Health health);
    bool apply_fill(protocol::Side side, std::int64_t quantity);
    protocol::RiskDecision evaluate(const protocol::OrderIntent& intent, std::uint64_t now_ns);
    protocol::PositionSnapshot position() const;
    protocol::LimitSnapshot limits() const;

private:
    protocol::RiskDecision reject(std::uint64_t correlation_id, std::uint64_t now_ns, std::uint16_t reason);
    core::EventJournal& journal_;
    mutable std::mutex mutex_;
    protocol::LimitSnapshot limits_{};
    protocol::PositionSnapshot position_{};
    Health health_{Health::Halted};
    std::uint64_t orders_this_second_{0};
    std::uint64_t second_epoch_ns_{0};
};

}
