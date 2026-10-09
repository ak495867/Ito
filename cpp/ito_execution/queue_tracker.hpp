#pragma once

#include <algorithm>
#include <cstdint>

namespace ito::execution {

struct RestingQueueOrder {
    std::uint64_t order_id{0};
    std::int64_t price_ticks{0};
    std::int64_t remaining_quantity{0};
    std::int64_t queue_ahead{0};
    bool is_buy{true};
};

class QueueTracker {
public:
    QueueTracker() = default;

    static RestingQueueOrder create_order(std::uint64_t id, bool is_buy, std::int64_t price, std::int64_t qty, std::int64_t depth_ahead) {
        return RestingQueueOrder{id, price, qty, std::max<std::int64_t>(0, depth_ahead), is_buy};
    }

    static std::int64_t process_trade(RestingQueueOrder& order, std::int64_t trade_price, std::int64_t trade_quantity, double cancellation_decay = 0.1) {
        const bool matches = (order.is_buy && trade_price <= order.price_ticks) || (!order.is_buy && trade_price >= order.price_ticks);
        if (!matches || trade_quantity <= 0) {
            return 0;
        }
        const auto decayed_queue = static_cast<std::int64_t>(order.queue_ahead * (1.0 - cancellation_decay));
        if (trade_quantity > decayed_queue) {
            const auto fillable = trade_quantity - decayed_queue;
            const auto filled = std::min(order.remaining_quantity, fillable);
            order.remaining_quantity -= filled;
            order.queue_ahead = 0;
            return filled;
        }
        order.queue_ahead = decayed_queue - trade_quantity;
        return 0;
    }
};

}
