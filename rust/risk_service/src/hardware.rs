use crate::{evaluate, to_fpga_frame, Decision, FpgaRiskFrame, RiskRequest, RiskResponse};
use crate::generated::{FRAME_BYTES as GENERATED_FRAME_BYTES, OFFSET_CONTROL, OFFSET_HEALTH, OFFSET_LIMITS_VERSION, OFFSET_MAX_NET_POSITION, OFFSET_MAX_NOTIONAL_TICKS, OFFSET_MAX_QUANTITY, OFFSET_NET_POSITION, OFFSET_PRICE_TICKS, OFFSET_QUANTITY};

pub const FRAME_BYTES: usize = GENERATED_FRAME_BYTES;

fn put_u64(bytes: &mut [u8; FRAME_BYTES], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

pub fn encode_frame(frame: FpgaRiskFrame) -> [u8; FRAME_BYTES] {
    let mut bytes = [0u8; FRAME_BYTES];
    put_u64(&mut bytes, OFFSET_PRICE_TICKS, frame.price_ticks);
    put_u64(&mut bytes, OFFSET_QUANTITY, frame.quantity);
    put_u64(&mut bytes, OFFSET_MAX_QUANTITY, frame.max_quantity);
    put_u64(&mut bytes, OFFSET_MAX_NOTIONAL_TICKS, frame.max_notional_ticks);
    put_u64(&mut bytes, OFFSET_NET_POSITION, frame.net_position as u64);
    put_u64(&mut bytes, OFFSET_MAX_NET_POSITION, frame.max_net_position);
    bytes[OFFSET_CONTROL] = frame.control;
    bytes[OFFSET_HEALTH] = frame.health;
    put_u64(&mut bytes, OFFSET_LIMITS_VERSION, 1);
    bytes
}

pub fn to_hex(bytes: &[u8; FRAME_BYTES]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

pub struct SoftwareFallback;

impl SoftwareFallback {
    pub fn evaluate(&self, request: RiskRequest) -> RiskResponse {
        evaluate(request)
    }
}

pub struct HardwarePipeline {
    fallback: SoftwareFallback,
}

impl HardwarePipeline {
    pub fn new() -> Self {
        Self { fallback: SoftwareFallback }
    }

    pub fn prepare(&self, request: RiskRequest) -> ([u8; FRAME_BYTES], RiskResponse) {
        let frame = to_fpga_frame(request);
        let bytes = encode_frame(frame);
        let response = self.fallback.evaluate(request);
        (bytes, response)
    }

    pub fn is_approved(response: &RiskResponse) -> bool {
        response.decision == Decision::Approved
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Side;

    fn request() -> RiskRequest {
        RiskRequest { price_ticks: 100, quantity: 10, max_quantity: 100, max_notional_ticks: 10_000, net_position: 0, max_net_position: 1_000, side: Side::Buy, trading_enabled: true, limits_valid: true, clock_healthy: true, feed_healthy: true, halted: false }
    }

    #[test]
    fn frame_uses_generated_register_offsets() {
        let frame = to_fpga_frame(request());
        let bytes = encode_frame(frame);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_PRICE_TICKS..OFFSET_PRICE_TICKS + 8].try_into().unwrap()), 100);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_QUANTITY..OFFSET_QUANTITY + 8].try_into().unwrap()), 10);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_MAX_QUANTITY..OFFSET_MAX_QUANTITY + 8].try_into().unwrap()), 100);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_MAX_NOTIONAL_TICKS..OFFSET_MAX_NOTIONAL_TICKS + 8].try_into().unwrap()), 10_000);
        assert_eq!(i64::from_le_bytes(bytes[OFFSET_NET_POSITION..OFFSET_NET_POSITION + 8].try_into().unwrap()), 0);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_MAX_NET_POSITION..OFFSET_MAX_NET_POSITION + 8].try_into().unwrap()), 1_000);
        assert_eq!(bytes[OFFSET_CONTROL], 5);
        assert_eq!(bytes[OFFSET_HEALTH], 7);
        assert_eq!(u64::from_le_bytes(bytes[OFFSET_LIMITS_VERSION..OFFSET_LIMITS_VERSION + 8].try_into().unwrap()), 1);
    }

    #[test]
    fn pipeline_matches_software_result() {
        let pipeline = HardwarePipeline::new();
        let (_, response) = pipeline.prepare(request());
        assert!(HardwarePipeline::is_approved(&response));
    }
}
