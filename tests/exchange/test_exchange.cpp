#include "../../cpp/ito_exchange/exchange_simulator.hpp"

#include <cassert>

namespace {
ito::protocol::OrderIntent order(std::uint64_t id, ito::protocol::Side side, ito::protocol::TimeInForce tif, std::int64_t price, std::int64_t quantity) {
    return ito::protocol::OrderIntent{id, id, 7, 11, 21, 101, 5, 33, side, ito::protocol::OrderType::Limit, tif, price, quantity, 1};
}
}

int main() {
    ito::core::EventJournal journal;
    ito::exchange::ExchangeSimulator exchange(journal);
    const auto maker_one = exchange.submit(order(1, ito::protocol::Side::Sell, ito::protocol::TimeInForce::Day, 101, 5), 10);
    const auto maker_two = exchange.submit(order(2, ito::protocol::Side::Sell, ito::protocol::TimeInForce::Day, 101, 7), 11);
    assert(maker_one.accepted && maker_two.accepted);
    assert(exchange.best_ask() == 101);
    const auto taker = exchange.submit(order(3, ito::protocol::Side::Buy, ito::protocol::TimeInForce::IOC, 101, 10), 12);
    assert(taker.accepted);
    assert(taker.matches.size() == 2);
    assert(taker.matches[0].maker_order_id == maker_one.venue_order_id);
    assert(taker.matches[0].quantity == 5);
    assert(taker.matches[1].maker_order_id == maker_two.venue_order_id);
    assert(taker.matches[1].quantity == 5);
    const auto remaining = exchange.find(maker_two.venue_order_id);
    assert(remaining.has_value() && remaining->remaining_quantity == 2);
    assert(exchange.cancel(maker_two.venue_order_id, 13));
    assert(exchange.resting_count() == 0);
    const auto invalid = exchange.submit(order(4, ito::protocol::Side::Buy, ito::protocol::TimeInForce::Day, 0, 1), 14);
    assert(!invalid.accepted);
    return 0;
}
