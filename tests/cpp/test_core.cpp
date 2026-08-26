#include "../../cpp/ito_execution/execution_engine.hpp"

#include <cassert>

int main() {
    ito::core::EventJournal journal;
    ito::risk::RiskEngine risk_engine(journal);
    risk_engine.set_limits(ito::protocol::LimitSnapshot{1, 10'000'000'000ULL, 100, 1'000, 100, 200, 2, true});
    risk_engine.set_position(ito::protocol::PositionSnapshot{0, 0});
    risk_engine.set_health(ito::risk::Health::Healthy);

    const ito::protocol::OrderIntent intent{1, 5001, 7, 11, 21, 101, 5, 33, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::Day, 100, 10, 1};
    const auto approved = risk_engine.evaluate(intent, 2);
    assert(approved.status == ito::protocol::RiskStatus::Approved);

    const auto rejected = risk_engine.evaluate(intent, 3);
    assert(rejected.status == ito::protocol::RiskStatus::Approved);
    const auto rate_rejected = risk_engine.evaluate(intent, 4);
    assert(rate_rejected.status == ito::protocol::RiskStatus::Rejected);

    ito::execution::ExecutionEngine engine(journal, risk_engine);
    engine.set_gateway_state(ito::execution::GatewayState::Ready);
    engine.set_halted(false);
    const auto sent = engine.submit(intent, 2'000'000'000ULL);
    assert(sent.has_value());
    assert(engine.acknowledge(intent.correlation_id, sent->venue_order_id, 2'000'000'100ULL));
    assert(!engine.acknowledge(999, 999, 2'000'000'200ULL));
    assert(engine.events().size() == 1);
    assert(journal.snapshot().size() >= 4);
    return 0;
}
