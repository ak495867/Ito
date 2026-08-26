#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
python3 scripts/check_no_comments.py
mkdir -p build/readiness
python3 scripts/production/readiness_check.py --output build/readiness/readiness.json || test $? -eq 1
rm -rf build/recovery
mkdir -p build/recovery
python3 scripts/operations/backup_restore.py backup --root "$root" --output build/recovery/ito-config.tar.gz --path config/risk/default_risk_policy.json --path interfaces/register_maps/risk_gate.json --path infra/docker/branch-nodes.json
python3 scripts/operations/backup_restore.py restore --archive build/recovery/ito-config.tar.gz --destination build/recovery/restored
python3 scripts/operations/health_report.py --readiness build/readiness/readiness.json --recovery build/recovery/ito-config.tar.gz --output build/readiness/health.json --prometheus build/readiness/ito.prom
python3 scripts/operations/key_rotation_drill.py --output build/release/key_rotation.json
mkdir -p build/portfolio
PYTHONPATH=python/portfolio python3 scripts/operations/portfolio_snapshot.py tests/portfolio/portfolio_case.json --output build/portfolio/snapshot.json
PYTHONPATH=python/operations python3 python/operations/prometheus_exporter.py --health build/readiness/health.json --portfolio build/portfolio/snapshot.json --output build/readiness/portfolio.prom
python3 scripts/generate_risk_interface.py
cmake -S . -B build/cpp -DCMAKE_BUILD_TYPE=Debug
cmake --build build/cpp
ctest --test-dir build/cpp --output-on-failure
cargo test --workspace --manifest-path rust/Cargo.toml
cargo run --quiet --manifest-path rust/Cargo.toml -p ito-connectivity-guard
mkdir -p build/release
cargo run --quiet --manifest-path rust/Cargo.toml -p ito-policy-signer -- config/risk/default_risk_policy.json rtl/common/generated/risk_frame_pkg.sv interfaces/schemas/order_intent.schema.json > build/release/binding.json
python3 scripts/operations/verify_release_binding.py --binding build/release/binding.json --policy config/risk/default_risk_policy.json --rtl rtl/common/generated/risk_frame_pkg.sv --schema interfaces/schemas/order_intent.schema.json
python3 scripts/operations/production_gate_simulations.py --root "$root" --output build/readiness/production_gate_simulations.json
python3 scripts/operations/generate_sbom.py --root "$root" --output build/release/sbom.json
mkdir -p build/hardware
cargo run --quiet --manifest-path rust/risk_service/Cargo.toml -- --emit-frame < tests/hardware/risk_request.json > build/hardware/risk_response.json
python3 scripts/check_hardware_response.py build/hardware/risk_response.json
dune build --root ocaml
dune exec --root ocaml policy_engine/risk_policy_validator.exe -- config/risk/default_risk_policy.json config/circuit_breakers/default_circuit_breakers.json
dune exec --root ocaml circuit_breaker/dynamic_engine.exe
PYTHONPATH=python/replay:python/ops_tools python3 -m unittest discover -s tests/python
python3 python/connectivity/config_linter.py
python3 scripts/run_benchmark_suite.py --branches 4 --messages-per-branch 5000 --venue-adapters exchange-a-sim,exchange-b-sim,broker-a-sim,broker-b-sim --output docs/benchmarks/multibranch_suite.json
python3 scripts/render_benchmark_suite.py docs/benchmarks/multibranch_suite.json docs/benchmarks
mkdir -p build/vectors build/rtl
build/cpp/ito_exchange_simulator --emit build/vectors/exchange_vectors.hex
iverilog -g2012 -o build/rtl/ito_tb rtl/common/ito_types.sv rtl/risk_gate/pre_trade_gate.sv rtl/tb/pre_trade_gate_tb.sv
vvp build/rtl/ito_tb
iverilog -g2012 -o build/rtl/ito_exchange_tb rtl/common/ito_types.sv rtl/risk_gate/pre_trade_gate.sv rtl/tb/exchange_bridge_tb.sv
vvp build/rtl/ito_exchange_tb
iverilog -g2012 -o build/rtl/ito_risk_accelerator_tb rtl/common/generated/risk_frame_pkg.sv rtl/risk_gate/risk_accelerator.sv rtl/tb/risk_accelerator_tb.sv
vvp build/rtl/ito_risk_accelerator_tb
iverilog -g2012 -o build/rtl/ito_connectivity_control_tb rtl/common/generated/risk_frame_pkg.sv rtl/risk_gate/risk_accelerator.sv rtl/protocol_bridge/order_frame_bridge.sv rtl/venue_adapters/venue_mux.sv rtl/tb/connectivity_control_tb.sv
vvp build/rtl/ito_connectivity_control_tb
iverilog -g2012 -o build/rtl/ito_rate_limiter_tb rtl/telemetry/rate_limiter.sv rtl/tb/rate_limiter_tb.sv
vvp build/rtl/ito_rate_limiter_tb
