#pragma once

#include <cstdint>
#include <string>

namespace ito::risk {

struct LimitSnapshot {
    std::uint64_t version{};
    std::uint64_t expires_at_ns{};
    std::int64_t max_order_quantity{};
    std::int64_t max_order_notional_ticks{};
    std::int64_t max_net_position{};
    std::int64_t max_orders_per_second{};
    bool trading_enabled{};
    bool fail_closed{true};
};

class LimitSnapshotGuard {
public:
    bool activate(LimitSnapshot snapshot, std::uint64_t now_ns);
    bool valid(std::uint64_t now_ns) const;
    const LimitSnapshot& active() const;
    std::string status(std::uint64_t now_ns) const;

private:
    LimitSnapshot active_{};
    bool initialized_{false};
};

}
