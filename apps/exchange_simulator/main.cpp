#include "../../cpp/ito_exchange/exchange_simulator.hpp"

#include <fstream>
#include <iostream>
#include <string>

namespace {
ito::protocol::OrderIntent intent(std::uint64_t correlation_id, ito::protocol::Side side, ito::protocol::OrderType type, ito::protocol::TimeInForce tif, std::int64_t price, std::int64_t quantity) {
    return ito::protocol::OrderIntent{correlation_id, correlation_id, 7, 11, 21, 101, 5, 33, side, type, tif, price, quantity, 1};
}

bool emit_vectors(const std::string& path) {
    std::ofstream output(path);
    if (!output.good()) {
        return false;
    }
    const std::uint64_t max_quantity = 100;
    const std::uint64_t max_notional = 10'000;
    const std::uint64_t cases[][5] = {
        {100, 10, max_quantity, max_notional, 1},
        {100, 101, max_quantity, max_notional, 0},
        {2'000, 10, max_quantity, max_notional, 0},
        {100, 10, 5, max_notional, 0}
    };
    for (const auto& test_case : cases) {
        for (const auto value : test_case) {
            output << std::hex << value << '\n';
        }
    }
    return output.good();
}
}

int main(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "--emit") {
        return emit_vectors(argv[2]) ? 0 : 1;
    }

    ito::core::EventJournal journal;
    ito::exchange::ExchangeSimulator simulator(journal);
    const auto sell = simulator.submit(intent(1001, ito::protocol::Side::Sell, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 101, 25), 10);
    const auto buy = simulator.submit(intent(1002, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 101, 10), 20);
    if (!sell.accepted || !buy.accepted || buy.matches.size() != 1 || buy.matches.front().quantity != 10 || simulator.resting_count() != 1) {
        return 2;
    }
    const auto resting = simulator.find(sell.venue_order_id);
    if (!resting.has_value() || resting->remaining_quantity != 15) {
        return 3;
    }
    if (!simulator.cancel(sell.venue_order_id, 30) || simulator.resting_count() != 0) {
        return 4;
    }
    std::cout << "exchange_simulator_pass" << '\n';
    return 0;
}
