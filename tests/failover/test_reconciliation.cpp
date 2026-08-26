#include "../../cpp/ito_reconciliation/reconciler.hpp"

#include <cassert>

int main() {
    ito::reconciliation::Reconciler reconciler;
    const std::vector<ito::reconciliation::LocalOrderState> local{{1, 11, 10, 0, 100}, {2, 12, 5, 0, 100}};
    const std::vector<ito::connectivity::ExecutionReport> venue{{11, 1, 50, 1, ito::connectivity::ExecutionStatus::Filled, 100, 10, 0, 1, 2, 0}, {12, 2, 50, 2, ito::connectivity::ExecutionStatus::Filled, 100, 2, 0, 1, 2, 0}, {13, 3, 50, 3, ito::connectivity::ExecutionStatus::Filled, 100, 2, 0, 1, 2, 0}};
    const auto findings = reconciler.compare(5, local, venue);
    assert(findings.size() == 3);
    bool matched = false;
    bool missing = false;
    bool mismatch = false;
    for (const auto& finding : findings) {
        matched = matched || finding.state == ito::reconciliation::ReconciliationState::Matched;
        missing = missing || finding.state == ito::reconciliation::ReconciliationState::MissingLocal;
        mismatch = mismatch || finding.state == ito::reconciliation::ReconciliationState::QuantityMismatch;
    }
    assert(matched && missing && mismatch);
    return 0;
}
