#pragma once

#include "venue_adapter.hpp"
#include "../ito_exchange/exchange_simulator.hpp"

#include <unordered_map>

namespace ito::connectivity {

class SimulatorAdapter final : public VenueAdapter {
public:
    SimulatorAdapter(core::EventJournal& journal, VenueIdentity identity);
    VenueIdentity identity() const override;
    SessionStatus status() const override;
    bool connect(std::uint64_t now_ns) override;
    void disconnect(std::uint64_t now_ns) override;
    std::optional<ExecutionReport> submit(const NormalizedOrder& order, std::uint64_t now_ns) override;
    std::optional<ExecutionReport> cancel(std::uint64_t client_order_id, std::uint64_t now_ns) override;
    std::vector<ExecutionReport> poll(std::uint64_t now_ns) override;

private:
    core::EventJournal& journal_;
    VenueIdentity identity_;
    SessionStatus status_{SessionStatus::Disabled};
    exchange::ExchangeSimulator exchange_;
    std::uint64_t next_execution_id_{1};
    std::unordered_map<std::uint64_t, std::uint64_t> client_to_venue_;
};

}
