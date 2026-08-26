#include "limit_snapshot.hpp"

namespace ito::risk {

bool LimitSnapshotGuard::activate(LimitSnapshot snapshot, std::uint64_t now_ns) {
    if (snapshot.version == 0 || snapshot.expires_at_ns <= now_ns || snapshot.max_order_quantity <= 0 || snapshot.max_order_notional_ticks <= 0 || snapshot.max_net_position <= 0 || snapshot.max_orders_per_second <= 0) {
        return false;
    }
    if (initialized_ && snapshot.version <= active_.version) {
        return false;
    }
    active_ = snapshot;
    initialized_ = true;
    return true;
}

bool LimitSnapshotGuard::valid(std::uint64_t now_ns) const {
    return initialized_ && active_.trading_enabled && active_.expires_at_ns > now_ns;
}

const LimitSnapshot& LimitSnapshotGuard::active() const {
    return active_;
}

std::string LimitSnapshotGuard::status(std::uint64_t now_ns) const {
    if (!initialized_) {
        return "uninitialized";
    }
    if (active_.expires_at_ns <= now_ns) {
        return "expired";
    }
    if (!active_.trading_enabled) {
        return "disabled";
    }
    return "valid";
}

}
