#include "../../cpp/ito_risk/risk_engine.hpp"

#include <iostream>

int main() {
    ito::core::EventJournal journal;
    ito::risk::RiskEngine risk_engine(journal);
    risk_engine.set_limits(ito::protocol::LimitSnapshot{4, 10'000, 100, 1'000, 100, 200, 10, true});
    risk_engine.set_health(ito::risk::Health::Healthy);
    const ito::protocol::OrderIntent intent{2, 9010, 8, 12, 22, 102, 5, 34, ito::protocol::Side::Buy, ito::protocol::OrderType::Limit, ito::protocol::TimeInForce::IOC, 10, 10, 1};
    const auto decision = risk_engine.evaluate(intent, 2'000);
    std::cout << static_cast<int>(decision.status) << ':' << decision.reason_code << '\n';
    return decision.status == ito::protocol::RiskStatus::Rejected ? 0 : 1;
}
