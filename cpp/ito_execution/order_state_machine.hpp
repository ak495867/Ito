#pragma once

#include <cstdint>
#include <string>

namespace ito::execution {

enum class OrderState : std::uint8_t { Created = 1, RiskApproved = 2, Sent = 3, Accepted = 4, PartiallyFilled = 5, Filled = 6, CancelPending = 7, Cancelled = 8, Rejected = 9, Uncertain = 10 };
enum class OrderEvent : std::uint8_t { RiskApprove = 1, Submit = 2, VenueAccept = 3, Fill = 4, CancelRequest = 5, CancelConfirm = 6, Reject = 7, RecoveryRequired = 8 };

class OrderStateMachine {
public:
    explicit OrderStateMachine(std::uint64_t client_order_id, std::int64_t order_quantity = 0);
    bool apply(OrderEvent event, std::int64_t fill_quantity = 0);
    OrderState state() const;
    std::uint64_t client_order_id() const;
    bool terminal() const;
    std::int64_t filled_quantity() const;
    std::int64_t remaining_quantity() const;
    std::string state_name() const;

private:
    std::uint64_t client_order_id_{};
    OrderState state_{OrderState::Created};
    std::int64_t order_quantity_{};
    std::int64_t filled_quantity_{};
};

}
