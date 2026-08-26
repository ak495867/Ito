#include "order_state_machine.hpp"

namespace ito::execution {

OrderStateMachine::OrderStateMachine(std::uint64_t client_order_id, std::int64_t order_quantity) : client_order_id_(client_order_id), order_quantity_(order_quantity) {}

bool OrderStateMachine::apply(OrderEvent event, std::int64_t fill_quantity) {
    switch (event) {
        case OrderEvent::RiskApprove:
            if (state_ != OrderState::Created) return false;
            state_ = OrderState::RiskApproved;
            return true;
        case OrderEvent::Submit:
            if (state_ != OrderState::RiskApproved) return false;
            state_ = OrderState::Sent;
            return true;
        case OrderEvent::VenueAccept:
            if (state_ != OrderState::Sent) return false;
            state_ = OrderState::Accepted;
            return true;
        case OrderEvent::Fill:
            if (state_ != OrderState::Accepted && state_ != OrderState::PartiallyFilled) return false;
            if (fill_quantity <= 0 || (order_quantity_ > 0 && (filled_quantity_ > order_quantity_ - fill_quantity))) return false;
            filled_quantity_ += fill_quantity;
            state_ = order_quantity_ > 0 && filled_quantity_ >= order_quantity_ ? OrderState::Filled : OrderState::PartiallyFilled;
            return true;
        case OrderEvent::CancelRequest:
            if (state_ != OrderState::Accepted && state_ != OrderState::PartiallyFilled) return false;
            state_ = OrderState::CancelPending;
            return true;
        case OrderEvent::CancelConfirm:
            if (state_ != OrderState::CancelPending) return false;
            state_ = OrderState::Cancelled;
            return true;
        case OrderEvent::Reject:
            if (state_ != OrderState::Sent && state_ != OrderState::RiskApproved) return false;
            state_ = OrderState::Rejected;
            return true;
        case OrderEvent::RecoveryRequired:
            if (terminal()) return false;
            state_ = OrderState::Uncertain;
            return true;
    }
    return false;
}

OrderState OrderStateMachine::state() const {
    return state_;
}

std::uint64_t OrderStateMachine::client_order_id() const {
    return client_order_id_;
}

bool OrderStateMachine::terminal() const {
    return state_ == OrderState::Filled || state_ == OrderState::Cancelled || state_ == OrderState::Rejected;
}

std::int64_t OrderStateMachine::filled_quantity() const {
    return filled_quantity_;
}

std::int64_t OrderStateMachine::remaining_quantity() const {
    return order_quantity_ > filled_quantity_ ? order_quantity_ - filled_quantity_ : 0;
}

std::string OrderStateMachine::state_name() const {
    switch (state_) {
        case OrderState::Created: return "created";
        case OrderState::RiskApproved: return "risk_approved";
        case OrderState::Sent: return "sent";
        case OrderState::Accepted: return "accepted";
        case OrderState::PartiallyFilled: return "partially_filled";
        case OrderState::Filled: return "filled";
        case OrderState::CancelPending: return "cancel_pending";
        case OrderState::Cancelled: return "cancelled";
        case OrderState::Rejected: return "rejected";
        case OrderState::Uncertain: return "uncertain";
    }
    return "unknown";
}

}
