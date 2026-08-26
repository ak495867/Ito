# Ito Risk Hardware-Acceleration Pipeline

## Scope

The Ito Rust risk microservice prepares a fixed-width request frame from the canonical risk request. The generated register-map artifacts define the shared offsets used by Rust serialization and SystemVerilog interpretation. The SystemVerilog accelerator captures one request, evaluates the safety predicates in a deterministic pipeline, and returns a registered decision and four-bit reason code.

## Data path

```text
Rust JSON request
    -> RiskRequest
    -> generated register-map constants
    -> FpgaRiskFrame
    -> 64-byte little-endian frame
    -> FPGA request capture
    -> arithmetic and health checks
    -> registered decision
    -> approved or reason code
```

## Frame layout

| Byte range | Meaning | Source |
| --- | --- | --- |
| 0..7 | Price ticks | `RiskRequest.price_ticks` |
| 8..15 | Quantity | `RiskRequest.quantity` |
| 16..23 | Maximum quantity | Generated `MAX_QUANTITY` offset |
| 24..31 | Maximum notional ticks | Generated `MAX_NOTIONAL_TICKS` offset |
| 32..39 | Net position | `RiskRequest.net_position` |
| 40..47 | Maximum net position | Generated `MAX_NET_POSITION` offset |
| 48 | Control bits | Trading enabled, halted, and side-buy flag |
| 49 | Health bits | Limits, clock, and feed health |
| 50..55 | Reserved | Zero-filled |
| 56..63 | Register-map version marker | Generated `LIMITS_VERSION` offset |

## Pipeline stages

| Stage | Operation | Output |
| --- | --- | --- |
| Capture | Latch request fields on `request_valid` | Stage-one request registers |
| Validate | Check control, limits, health, quantity, notional, and position | Combinational decision and reason |
| Commit | Register response and reason code | `response_valid`, `approved`, `reason_code` |

The control byte uses bit zero for trading enabled, bit one for halted, and bit two for the buy-side flag. The pipeline is fail-closed. Trading-disabled, halted, invalid-limit, clock-unhealthy, feed-unhealthy, quantity, price, notional, position, and arithmetic-invalid requests are rejected. Rust retains a software fallback for deterministic comparison and laboratory operation; this fallback is not a bypass for production approval.

## Generated artifacts

The canonical source is `interfaces/register_maps/risk_gate.json`. `scripts/generate_risk_interface.py` derives:

- `rust/risk_service/src/generated.rs`;
- `rtl/common/generated/risk_frame_pkg.sv`;
- `interfaces/generated/risk_frame_layout.json`.

The generator runs before C++/Rust/RTL integration in the unified build. Changes to the register map therefore produce a visible diff in every language boundary.

## Verification

The Rust library verifies every encoded field against generated offsets and software fallback behavior. The SystemVerilog testbench verifies a valid request, quantity rejection, sell-side lower-bound rejection, and response alignment. The unified build runs the Rust tests, emits a frame from the service, checks the fixed frame size, compiles the generated SystemVerilog package and accelerator, and executes the testbench.

## Production gate

This pipeline is a simulator and verification foundation. A production FPGA release additionally requires vendor synthesis, timing closure, CDC analysis, formal properties, board-level hardware-in-the-loop testing, signed bitstream release, measured deployment identity, venue certification, and independent risk approval.
