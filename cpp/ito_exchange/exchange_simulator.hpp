#pragma once

#include "../ito_core/event.hpp"

#include <cstdint>
#include <deque>
#include <map>
#include <optional>
#include <unordered_map>
#include <vector>

namespace ito::exchange {

struct RestingOrder {
    std::uint64_t venue_order_id{};
    std::uint64_t correlation_id{};
    protocol::Side side{protocol::Side::Buy};
    std::int64_t price_ticks{};
    std::int64_t remaining_quantity{};
    std::uint64_t sequence{};
};

struct MatchEvent {
    std::uint64_t taker_order_id{};
    std::uint64_t maker_order_id{};
    std::int64_t price_ticks{};
    std::int64_t quantity{};
    std::uint64_t timestamp_ns{};
};

struct SubmitResult {
    std::uint64_t venue_order_id{};
    std::int64_t remaining_quantity{};
    std::vector<MatchEvent> matches;
    bool accepted{};
};

class ExchangeSimulator {
public:
    explicit ExchangeSimulator(core::EventJournal& journal);
    SubmitResult submit(const protocol::OrderIntent& intent, std::uint64_t timestamp_ns);
    bool cancel(std::uint64_t venue_order_id, std::uint64_t timestamp_ns);
    std::optional<RestingOrder> find(std::uint64_t venue_order_id) const;
    std::int64_t best_bid() const;
    std::int64_t best_ask() const;
    std::size_t resting_count() const;

private:
    using BookLevel = std::deque<RestingOrder>;
    using BidBook = std::map<std::int64_t, BookLevel, std::greater<>>;
    using AskBook = std::map<std::int64_t, BookLevel>;

    std::uint64_t next_order_id_{};
    core::EventJournal& journal_;
    BidBook bids_;
    AskBook asks_;
    std::unordered_map<std::uint64_t, RestingOrder> index_;

    void remove_from_index(std::uint64_t venue_order_id);
    SubmitResult match_buy(const protocol::OrderIntent& intent, std::uint64_t order_id, std::uint64_t timestamp_ns);
    SubmitResult match_sell(const protocol::OrderIntent& intent, std::uint64_t order_id, std::uint64_t timestamp_ns);
    void rest(const RestingOrder& order);
};

}
