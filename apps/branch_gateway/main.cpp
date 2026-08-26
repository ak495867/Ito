#include "../../cpp/ito_execution/execution_engine.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

int main() {
    ito::core::EventJournal journal;
    ito::risk::RiskEngine risk_engine(journal);
    risk_engine.set_limits(ito::protocol::LimitSnapshot{1, 10'000'000'000ULL, 100, 1'000'000, 1'000, 2'000, 10, true});
    risk_engine.set_health(ito::risk::Health::Healthy);
    ito::execution::ExecutionEngine engine(journal, risk_engine);
    engine.set_gateway_state(ito::execution::GatewayState::Ready);
    const char* configured_mode = std::getenv("ITO_MODE");
    const std::string mode = configured_mode == nullptr || std::string(configured_mode).empty() ? "restricted" : configured_mode;
    if (mode != "restricted" && mode != "lab") {
        std::cerr << "invalid_mode" << '\n';
        return 2;
    }
    engine.set_halted(mode != "lab");
    std::cout << mode << '\n';
    return 0;
}
