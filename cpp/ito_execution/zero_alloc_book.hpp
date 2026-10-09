#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>

namespace ito::execution {

struct alignas(16) BookLevel {
    std::int64_t price_ticks{0};
    std::int64_t size{0};
    std::uint32_t order_count{0};
    std::uint32_t padding{0};
};

template <std::size_t MaxDepth = 32>
class alignas(64) ZeroAllocOrderBook {
public:
    ZeroAllocOrderBook() = default;

    void update_bid(std::int64_t price_ticks, std::int64_t size, std::uint32_t order_count = 1) {
        update_level(bids_, bid_count_, price_ticks, size, order_count, true);
    }

    void update_ask(std::int64_t price_ticks, std::int64_t size, std::uint32_t order_count = 1) {
        update_level(asks_, ask_count_, price_ticks, size, order_count, false);
    }

    void remove_bid(std::int64_t price_ticks) {
        remove_level(bids_, bid_count_, price_ticks);
    }

    void remove_ask(std::int64_t price_ticks) {
        remove_level(asks_, ask_count_, price_ticks);
    }

    std::int64_t best_bid() const {
        return bid_count_ > 0 ? bids_[0].price_ticks : 0;
    }

    std::int64_t best_ask() const {
        return ask_count_ > 0 ? asks_[0].price_ticks : 0;
    }

    std::int64_t mid_price() const {
        if (bid_count_ > 0 && ask_count_ > 0) {
            return (bids_[0].price_ticks + asks_[0].price_ticks) / 2;
        }
        return bid_count_ > 0 ? bids_[0].price_ticks : (ask_count_ > 0 ? asks_[0].price_ticks : 0);
    }

    std::int64_t spread() const {
        if (bid_count_ > 0 && ask_count_ > 0 && asks_[0].price_ticks >= bids_[0].price_ticks) {
            return asks_[0].price_ticks - bids_[0].price_ticks;
        }
        return 0;
    }

    std::size_t bid_depth() const { return bid_count_; }
    std::size_t ask_depth() const { return ask_count_; }

    const std::array<BookLevel, MaxDepth>& bids() const { return bids_; }
    const std::array<BookLevel, MaxDepth>& asks() const { return asks_; }

    struct ExecutionWalk {
        std::int64_t executed_quantity{0};
        std::int64_t vwap_ticks{0};
        std::int64_t slippage_ticks{0};
        std::int64_t levels_consumed{0};
    };

    ExecutionWalk walk_book(bool is_buy, std::int64_t requested_quantity) const {
        ExecutionWalk result{};
        if (requested_quantity <= 0) {
            return result;
        }
        const auto& ladder = is_buy ? asks_ : bids_;
        const auto depth = is_buy ? ask_count_ : bid_count_;
        const auto initial_mid = mid_price();

        std::int64_t remaining = requested_quantity;
        std::int64_t total_notional = 0;

        for (std::size_t i = 0; i < depth && remaining > 0; ++i) {
            const auto fill_qty = std::min(remaining, ladder[i].size);
            if (fill_qty <= 0) {
                continue;
            }
            total_notional += fill_qty * ladder[i].price_ticks;
            remaining -= fill_qty;
            result.executed_quantity += fill_qty;
            result.levels_consumed++;
        }

        if (result.executed_quantity > 0) {
            result.vwap_ticks = total_notional / result.executed_quantity;
            result.slippage_ticks = std::llabs(result.vwap_ticks - initial_mid);
        }
        return result;
    }

    void clear() {
        bid_count_ = 0;
        ask_count_ = 0;
    }

private:
    void update_level(std::array<BookLevel, MaxDepth>& ladder, std::size_t& count, std::int64_t price, std::int64_t size, std::uint32_t order_count, bool descending) {
        for (std::size_t i = 0; i < count; ++i) {
            if (ladder[i].price_ticks == price) {
                if (size <= 0) {
                    remove_at(ladder, count, i);
                } else {
                    ladder[i].size = size;
                    ladder[i].order_count = order_count;
                }
                return;
            }
        }
        if (size <= 0) {
            return;
        }
        std::size_t insert_pos = count;
        for (std::size_t i = 0; i < count; ++i) {
            const bool precedes = descending ? (price > ladder[i].price_ticks) : (price < ladder[i].price_ticks);
            if (precedes) {
                insert_pos = i;
                break;
            }
        }
        if (count < MaxDepth) {
            for (std::size_t i = count; i > insert_pos; --i) {
                ladder[i] = ladder[i - 1];
            }
            ladder[insert_pos] = BookLevel{price, size, order_count, 0};
            count++;
        } else if (insert_pos < MaxDepth) {
            for (std::size_t i = MaxDepth - 1; i > insert_pos; --i) {
                ladder[i] = ladder[i - 1];
            }
            ladder[insert_pos] = BookLevel{price, size, order_count, 0};
        }
    }

    void remove_level(std::array<BookLevel, MaxDepth>& ladder, std::size_t& count, std::int64_t price) {
        for (std::size_t i = 0; i < count; ++i) {
            if (ladder[i].price_ticks == price) {
                remove_at(ladder, count, i);
                return;
            }
        }
    }

    void remove_at(std::array<BookLevel, MaxDepth>& ladder, std::size_t& count, std::size_t idx) {
        for (std::size_t i = idx; i + 1 < count; ++i) {
            ladder[i] = ladder[i + 1];
        }
        count--;
        ladder[count] = BookLevel{};
    }

    std::size_t bid_count_{0};
    std::size_t ask_count_{0};
    std::array<BookLevel, MaxDepth> bids_{};
    std::array<BookLevel, MaxDepth> asks_{};
};

}
