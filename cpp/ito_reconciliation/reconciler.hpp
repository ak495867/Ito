#pragma once

#include "../ito_connectivity/venue_types.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace ito::reconciliation {

enum class ReconciliationState : std::uint8_t { Matched = 1, MissingLocal = 2, MissingVenue = 3, QuantityMismatch = 4, PriceMismatch = 5, Uncertain = 6 };

struct LocalOrderState {
    std::uint64_t client_order_id{};
    std::uint64_t correlation_id{};
    std::int64_t executed_quantity{};
    std::int64_t leaves_quantity{};
    std::int64_t average_price_ticks{};
};

struct ReconciliationFinding {
    std::uint16_t venue_id{};
    std::uint64_t client_order_id{};
    ReconciliationState state{ReconciliationState::Uncertain};
    std::string detail;
};

class Reconciler {
public:
    std::vector<ReconciliationFinding> compare(std::uint16_t venue_id, const std::vector<LocalOrderState>& local, const std::vector<connectivity::ExecutionReport>& venue) const;
};

}
