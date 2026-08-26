#include "../../cpp/ito_execution/execution_engine.hpp"

#include <iostream>

int main() {
    ito::core::EventJournal journal;
    ito::risk::RiskEngine risk_engine(journal);
    risk_engine.set_limits(ito::protocol::LimitSnapshot{1, 10'000'000'000ULL, 100, 1'000'000, 1'000, 2'000, 10, true});
    risk_engine.set_position(ito::protocol::PositionSnapshot{0, 0});
    risk_engine.set_health(ito::risk::Health::Healthy);

    ito::execution::ExecutionEngine engine(journal, risk_engine);
    engine.set_gateway_state(ito::execution::GatewayState::Ready);
    engine.set_halted(false);

    const ito::protocol::OrderIntent intent{1, 9001, 7, 11, 21, 101, 5, 33, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 100, 10, 1'000'000};
    const auto result = engine.submit(intent, 2'000'000);
    if (!result.has_value()) {
        return 2;
    }
    std::cout << result->venue_order_id << '\n';
    return engine.acknowledge(intent.correlation_id, result->venue_order_id, 3'000'000) ? 0 : 3;
}
