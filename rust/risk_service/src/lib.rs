pub mod generated;
pub mod hardware;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum Side {
    #[serde(rename = "buy", alias = "Buy")]
    Buy,
    #[serde(rename = "sell", alias = "Sell")]
    Sell,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct RiskRequest {
    pub price_ticks: u64,
    pub quantity: u64,
    pub max_quantity: u64,
    pub max_notional_ticks: u64,
    pub net_position: i64,
    pub max_net_position: u64,
    pub side: Side,
    pub trading_enabled: bool,
    pub limits_valid: bool,
    pub clock_healthy: bool,
    pub feed_healthy: bool,
    pub halted: bool,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum Decision {
    Approved,
    TradingDisabled,
    LimitsInvalid,
    HealthInvalid,
    QuantityInvalid,
    PriceInvalid,
    NotionalInvalid,
    PositionInvalid,
    ArithmeticOverflow,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct RiskResponse {
    pub decision: Decision,
    pub reason_code: u8,
    pub request_digest: String,
}

pub fn evaluate(request: RiskRequest) -> RiskResponse {
    let decision = if !request.trading_enabled || request.halted {
        Decision::TradingDisabled
    } else if !request.limits_valid {
        Decision::LimitsInvalid
    } else if !request.clock_healthy || !request.feed_healthy {
        Decision::HealthInvalid
    } else if request.quantity == 0 || request.quantity > request.max_quantity {
        Decision::QuantityInvalid
    } else if request.price_ticks == 0 {
        Decision::PriceInvalid
    } else if request.price_ticks.checked_mul(request.quantity).is_none() {
        Decision::ArithmeticOverflow
    } else if request.price_ticks * request.quantity > request.max_notional_ticks {
        Decision::NotionalInvalid
    } else {
        let signed = match request.side {
            Side::Buy => request.quantity as i128,
            Side::Sell => -(request.quantity as i128),
        };
        let next = request.net_position as i128 + signed;
        if next.unsigned_abs() > request.max_net_position as u128 {
            Decision::PositionInvalid
        } else {
            Decision::Approved
        }
    };
    let reason_code = match decision {
        Decision::Approved => 0,
        Decision::TradingDisabled => 1,
        Decision::LimitsInvalid => 2,
        Decision::HealthInvalid => 3,
        Decision::QuantityInvalid => 4,
        Decision::PriceInvalid => 5,
        Decision::NotionalInvalid => 6,
        Decision::PositionInvalid => 7,
        Decision::ArithmeticOverflow => 8,
    };
    let bytes = serde_json::to_vec(&request).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let request_digest = hasher.finalize().iter().map(|byte| format!("{byte:02x}")).collect();
    RiskResponse { decision, reason_code, request_digest }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct FpgaRiskFrame {
    pub price_ticks: u64,
    pub quantity: u64,
    pub max_quantity: u64,
    pub max_notional_ticks: u64,
    pub net_position: i64,
    pub max_net_position: u64,
    pub control: u8,
    pub health: u8,
}

pub fn to_fpga_frame(request: RiskRequest) -> FpgaRiskFrame {
    let control = (request.trading_enabled as u8) | ((request.halted as u8) << 1) | ((matches!(request.side, Side::Buy) as u8) << 2);
    let health = (request.limits_valid as u8) | ((request.clock_healthy as u8) << 1) | ((request.feed_healthy as u8) << 2);
    FpgaRiskFrame { price_ticks: request.price_ticks, quantity: request.quantity, max_quantity: request.max_quantity, max_notional_ticks: request.max_notional_ticks, net_position: request.net_position, max_net_position: request.max_net_position, control, health }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request() -> RiskRequest {
        RiskRequest { price_ticks: 100, quantity: 10, max_quantity: 100, max_notional_ticks: 10_000, net_position: 0, max_net_position: 1_000, side: Side::Buy, trading_enabled: true, limits_valid: true, clock_healthy: true, feed_healthy: true, halted: false }
    }

    #[test]
    fn approves_valid_request() {
        assert_eq!(evaluate(request()).decision, Decision::Approved);
    }

    #[test]
    fn rejects_zero_price() {
        let mut value = request();
        value.price_ticks = 0;
        assert_eq!(evaluate(value).decision, Decision::PriceInvalid);
    }

    #[test]
    fn accepts_lowercase_side_json() {
        let value: RiskRequest = serde_json::from_str("{\"price_ticks\":100,\"quantity\":10,\"max_quantity\":100,\"max_notional_ticks\":10000,\"net_position\":0,\"max_net_position\":1000,\"side\":\"buy\",\"trading_enabled\":true,\"limits_valid\":true,\"clock_healthy\":true,\"feed_healthy\":true,\"halted\":false}").unwrap();
        assert_eq!(value.side, Side::Buy);
    }

    #[test]
    fn rejects_unhealthy_request() {
        let mut value = request();
        value.clock_healthy = false;
        assert_eq!(evaluate(value).decision, Decision::HealthInvalid);
    }

    #[test]
    fn produces_fpga_frame() {
        let frame = to_fpga_frame(request());
        assert_eq!(frame.control, 5);
        assert_eq!(frame.health, 7);
    }
}
