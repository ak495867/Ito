#include "reconciler.hpp"

#include <unordered_map>

namespace ito::reconciliation {

std::vector<ReconciliationFinding> Reconciler::compare(std::uint16_t venue_id, const std::vector<LocalOrderState>& local, const std::vector<connectivity::ExecutionReport>& venue) const {
    std::unordered_map<std::uint64_t, LocalOrderState> local_by_id;
    std::unordered_map<std::uint64_t, connectivity::ExecutionReport> venue_by_id;
    for (const auto& order : local) {
        local_by_id[order.client_order_id] = order;
    }
    for (const auto& report : venue) {
        venue_by_id[report.client_order_id] = report;
    }
    std::vector<ReconciliationFinding> findings;
    for (const auto& [client_order_id, order] : local_by_id) {
        const auto found = venue_by_id.find(client_order_id);
        if (found == venue_by_id.end()) {
            findings.push_back(ReconciliationFinding{venue_id, client_order_id, ReconciliationState::MissingVenue, "venue_report_missing"});
            continue;
        }
        const auto& report = found->second;
        if (report.quantity < order.executed_quantity || report.leaves_quantity < 0) {
            findings.push_back(ReconciliationFinding{venue_id, client_order_id, ReconciliationState::QuantityMismatch, "quantity_inconsistent"});
        } else if (order.average_price_ticks > 0 && report.price_ticks > 0 && report.price_ticks != order.average_price_ticks) {
            findings.push_back(ReconciliationFinding{venue_id, client_order_id, ReconciliationState::PriceMismatch, "price_inconsistent"});
        } else {
            findings.push_back(ReconciliationFinding{venue_id, client_order_id, ReconciliationState::Matched, "matched"});
        }
    }
    for (const auto& [client_order_id, report] : venue_by_id) {
        static_cast<void>(report);
        if (!local_by_id.contains(client_order_id)) {
            findings.push_back(ReconciliationFinding{venue_id, client_order_id, ReconciliationState::MissingLocal, "local_order_missing"});
        }
    }
    return findings;
}

}
