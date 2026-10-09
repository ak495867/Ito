#pragma once

#include <cstdint>

namespace ito::risk {

enum class HardwareReasonCode : std::uint8_t {
    Approved = 0,
    HaltedOrDisabled = 1,
    LimitsInvalid = 2,
    FeedClockUnhealthy = 3,
    QuantityLimit = 4,
    NotionalLimit = 5,
    PositionLimit = 6,
    PriceZero = 7
};

struct HardwareGateInputs {
    bool intent_valid{false};
    bool side_buy{true};
    bool trading_enabled{true};
    bool limits_valid{true};
    bool clock_healthy{true};
    bool feed_healthy{true};
    bool halted{false};
    std::uint64_t price_ticks{0};
    std::uint64_t quantity{0};
    std::uint64_t max_quantity{0};
    std::uint64_t max_notional_ticks{0};
    std::int64_t net_position{0};
    std::uint64_t max_net_position{0};
};

struct HardwareGateOutputs {
    bool decision_valid{false};
    bool approved{false};
    HardwareReasonCode reason_code{HardwareReasonCode::Approved};
};

class HardwareRiskGateModel {
public:
    HardwareRiskGateModel() = default;

    void reset() {
        stage_valid_ = false;
        stage_side_buy_ = false;
        stage_trading_enabled_ = false;
        stage_limits_valid_ = false;
        stage_clock_healthy_ = false;
        stage_feed_healthy_ = false;
        stage_halted_ = false;
        stage_price_ticks_ = 0;
        stage_quantity_ = 0;
        stage_max_quantity_ = 0;
        stage_max_notional_ticks_ = 0;
        stage_net_position_ = 0;
        stage_max_net_position_ = 0;
        out_decision_valid_ = false;
        out_approved_ = false;
        out_reason_code_ = HardwareReasonCode::Approved;
    }

    HardwareGateOutputs step(const HardwareGateInputs& in) {
        if (stage_valid_) {
            const auto notional = static_cast<unsigned __int128>(stage_price_ticks_) * static_cast<unsigned __int128>(stage_quantity_);
            const std::int64_t signed_quantity = stage_side_buy_ ? static_cast<std::int64_t>(stage_quantity_) : -static_cast<std::int64_t>(stage_quantity_);
            const std::int64_t next_position = stage_net_position_ + signed_quantity;

            out_decision_valid_ = true;
            out_approved_ = false;

            if (!stage_trading_enabled_ || stage_halted_) {
                out_reason_code_ = HardwareReasonCode::HaltedOrDisabled;
            } else if (!stage_limits_valid_) {
                out_reason_code_ = HardwareReasonCode::LimitsInvalid;
            } else if (!stage_clock_healthy_ || !stage_feed_healthy_) {
                out_reason_code_ = HardwareReasonCode::FeedClockUnhealthy;
            } else if (stage_quantity_ == 0 || stage_quantity_ > stage_max_quantity_) {
                out_reason_code_ = HardwareReasonCode::QuantityLimit;
            } else if (notional > static_cast<unsigned __int128>(stage_max_notional_ticks_)) {
                out_reason_code_ = HardwareReasonCode::NotionalLimit;
            } else if (next_position > static_cast<std::int64_t>(stage_max_net_position_) || next_position < -static_cast<std::int64_t>(stage_max_net_position_)) {
                out_reason_code_ = HardwareReasonCode::PositionLimit;
            } else if (stage_price_ticks_ == 0) {
                out_reason_code_ = HardwareReasonCode::PriceZero;
            } else {
                out_approved_ = true;
                out_reason_code_ = HardwareReasonCode::Approved;
            }
        } else {
            out_decision_valid_ = false;
            out_approved_ = false;
            out_reason_code_ = HardwareReasonCode::Approved;
        }

        stage_valid_ = in.intent_valid;
        stage_side_buy_ = in.side_buy;
        stage_trading_enabled_ = in.trading_enabled;
        stage_limits_valid_ = in.limits_valid;
        stage_clock_healthy_ = in.clock_healthy;
        stage_feed_healthy_ = in.feed_healthy;
        stage_halted_ = in.halted;
        stage_price_ticks_ = in.price_ticks;
        stage_quantity_ = in.quantity;
        stage_max_quantity_ = in.max_quantity;
        stage_max_notional_ticks_ = in.max_notional_ticks;
        stage_net_position_ = in.net_position;
        stage_max_net_position_ = in.max_net_position;

        return HardwareGateOutputs{out_decision_valid_, out_approved_, out_reason_code_};
    }

private:
    bool stage_valid_{false};
    bool stage_side_buy_{false};
    bool stage_trading_enabled_{false};
    bool stage_limits_valid_{false};
    bool stage_clock_healthy_{false};
    bool stage_feed_healthy_{false};
    bool stage_halted_{false};
    std::uint64_t stage_price_ticks_{0};
    std::uint64_t stage_quantity_{0};
    std::uint64_t stage_max_quantity_{0};
    std::uint64_t stage_max_notional_ticks_{0};
    std::int64_t stage_net_position_{0};
    std::uint64_t stage_max_net_position_{0};

    bool out_decision_valid_{false};
    bool out_approved_{false};
    HardwareReasonCode out_reason_code_{HardwareReasonCode::Approved};
};

}
