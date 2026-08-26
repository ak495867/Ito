cmake_minimum_required(VERSION 3.20)
project(Ito VERSION 0.1.0 LANGUAGES CXX)
find_package(OpenSSL REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(ito_common INTERFACE)
target_include_directories(ito_common INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/cpp)
target_compile_options(ito_common INTERFACE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror)

add_library(ito_core STATIC cpp/ito_core/event.cpp)
target_link_libraries(ito_core PUBLIC ito_common)

add_library(ito_journal STATIC cpp/ito_journal/journal_file.cpp)
target_link_libraries(ito_journal PUBLIC ito_core ito_common)

add_library(ito_risk STATIC cpp/ito_risk/risk_engine.cpp)
target_link_libraries(ito_risk PUBLIC ito_core ito_common)

add_library(ito_execution STATIC cpp/ito_execution/execution_engine.cpp)
target_link_libraries(ito_execution PUBLIC ito_core ito_risk ito_common)

add_library(ito_exchange STATIC cpp/ito_exchange/exchange_simulator.cpp)
target_link_libraries(ito_exchange PUBLIC ito_core ito_common)

add_library(ito_connectivity STATIC cpp/ito_connectivity/endpoint_connector.cpp cpp/ito_connectivity/network_adapter.cpp cpp/ito_connectivity/simulator_adapter.cpp cpp/ito_connectivity/venue_registry.cpp)
target_link_libraries(ito_connectivity PUBLIC ito_exchange ito_core ito_common OpenSSL::SSL OpenSSL::Crypto)

add_library(ito_session STATIC cpp/ito_session/session_manager.cpp)
target_link_libraries(ito_session PUBLIC ito_connectivity ito_common)

add_library(ito_routing STATIC cpp/ito_routing/smart_order_router.cpp)
target_link_libraries(ito_routing PUBLIC ito_session ito_connectivity ito_common)

add_library(ito_reconciliation STATIC cpp/ito_reconciliation/reconciler.cpp)
target_link_libraries(ito_reconciliation PUBLIC ito_connectivity ito_common)

add_library(ito_state_machine STATIC cpp/ito_execution/order_state_machine.cpp)
target_link_libraries(ito_state_machine PUBLIC ito_common)

add_library(ito_limits STATIC cpp/ito_risk/limit_snapshot.cpp)
target_link_libraries(ito_limits PUBLIC ito_common)

add_library(ito_leases STATIC cpp/ito_session/lease_fencer.cpp)
target_link_libraries(ito_leases PUBLIC ito_common)

add_library(ito_observability STATIC cpp/ito_observability/metrics_registry.cpp)
target_link_libraries(ito_observability PUBLIC ito_common)

add_executable(ito_execution_host apps/execution_host/main.cpp)
target_link_libraries(ito_execution_host PRIVATE ito_execution ito_core ito_risk ito_journal ito_common)

add_executable(ito_risk_engine apps/risk_engine/main.cpp)
target_link_libraries(ito_risk_engine PRIVATE ito_risk ito_core ito_common)

add_executable(ito_branch_gateway apps/branch_gateway/main.cpp)
target_link_libraries(ito_branch_gateway PRIVATE ito_execution ito_core ito_risk ito_common)

add_executable(ito_operations_agent apps/operations_agent/main.cpp)
target_link_libraries(ito_operations_agent PRIVATE ito_execution ito_core ito_risk ito_common)

add_executable(ito_exchange_simulator apps/exchange_simulator/main.cpp)
target_link_libraries(ito_exchange_simulator PRIVATE ito_exchange ito_core ito_common)

add_executable(ito_venue_router apps/venue_router/main.cpp)
target_link_libraries(ito_venue_router PRIVATE ito_routing ito_session ito_connectivity ito_exchange ito_core ito_common ito_leases ito_state_machine ito_limits ito_observability ito_reconciliation)

enable_testing()
add_executable(ito_core_tests tests/cpp/test_core.cpp)
target_link_libraries(ito_core_tests PRIVATE ito_execution ito_core ito_risk ito_common)
add_test(NAME ito_core_tests COMMAND ito_core_tests)
add_executable(ito_journal_file_tests tests/cpp/test_journal_file.cpp)
target_link_libraries(ito_journal_file_tests PRIVATE ito_journal ito_core ito_common)
add_test(NAME ito_journal_file_tests COMMAND ito_journal_file_tests)
add_executable(ito_exchange_tests tests/exchange/test_exchange.cpp)
target_link_libraries(ito_exchange_tests PRIVATE ito_exchange ito_core ito_common)
add_test(NAME ito_exchange_tests COMMAND ito_exchange_tests)
add_executable(ito_multi_venue_tests tests/connectivity/test_multi_venue.cpp)
target_link_libraries(ito_multi_venue_tests PRIVATE ito_routing ito_session ito_connectivity ito_exchange ito_core ito_common)
add_test(NAME ito_multi_venue_tests COMMAND ito_multi_venue_tests)
add_executable(ito_endpoint_connector_tests tests/connectivity/test_endpoint_connector.cpp)
target_link_libraries(ito_endpoint_connector_tests PRIVATE ito_connectivity ito_common)
add_test(NAME ito_endpoint_connector_tests COMMAND ito_endpoint_connector_tests)
add_executable(ito_control_tests tests/routing/test_controls.cpp)
target_link_libraries(ito_control_tests PRIVATE ito_leases ito_state_machine ito_limits ito_observability ito_common)
add_test(NAME ito_control_tests COMMAND ito_control_tests)
add_executable(ito_reconciliation_tests tests/failover/test_reconciliation.cpp)
target_link_libraries(ito_reconciliation_tests PRIVATE ito_reconciliation ito_connectivity ito_exchange ito_core ito_common)
add_test(NAME ito_reconciliation_tests COMMAND ito_reconciliation_tests)

add_custom_target(ito_generate_risk_interface ALL
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_risk_interface.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_rust_build ALL
    COMMAND cargo build --manifest-path ${CMAKE_CURRENT_SOURCE_DIR}/rust/Cargo.toml
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_ocaml_build ALL
    COMMAND dune build
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/ocaml
)

add_custom_target(ito_exchange_vectors ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/vectors
    COMMAND $<TARGET_FILE:ito_exchange_simulator> --emit ${CMAKE_CURRENT_SOURCE_DIR}/build/vectors/exchange_vectors.hex
    DEPENDS ito_exchange_simulator
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_rtl_test ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl
    COMMAND iverilog -g2012 -o ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_tb ${CMAKE_CURRENT_SOURCE_DIR}/rtl/common/ito_types.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/risk_gate/pre_trade_gate.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/tb/pre_trade_gate_tb.sv
    COMMAND vvp ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_tb
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
add_dependencies(ito_rtl_test ito_exchange_vectors)

add_custom_target(ito_rtl_exchange_test ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl
    COMMAND iverilog -g2012 -o ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_exchange_tb ${CMAKE_CURRENT_SOURCE_DIR}/rtl/common/ito_types.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/risk_gate/pre_trade_gate.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/tb/exchange_bridge_tb.sv
    COMMAND vvp ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_exchange_tb
    DEPENDS ito_exchange_vectors
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_rtl_rate_test ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl
    COMMAND iverilog -g2012 -o ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_rate_limiter_tb ${CMAKE_CURRENT_SOURCE_DIR}/rtl/telemetry/rate_limiter.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/tb/rate_limiter_tb.sv
    COMMAND vvp ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_rate_limiter_tb
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_rtl_connectivity_test ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl
    COMMAND iverilog -g2012 -o ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_connectivity_control_tb ${CMAKE_CURRENT_SOURCE_DIR}/rtl/common/generated/risk_frame_pkg.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/risk_gate/risk_accelerator.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/protocol_bridge/order_frame_bridge.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/venue_adapters/venue_mux.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/tb/connectivity_control_tb.sv
    COMMAND vvp ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_connectivity_control_tb
    DEPENDS ito_generate_risk_interface
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_rtl_accelerator_test ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl
    COMMAND iverilog -g2012 -o ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_risk_accelerator_tb ${CMAKE_CURRENT_SOURCE_DIR}/rtl/common/generated/risk_frame_pkg.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/risk_gate/risk_accelerator.sv ${CMAKE_CURRENT_SOURCE_DIR}/rtl/tb/risk_accelerator_tb.sv
    COMMAND vvp ${CMAKE_CURRENT_SOURCE_DIR}/build/rtl/ito_risk_accelerator_tb
    DEPENDS ito_generate_risk_interface
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_dependencies(ito_rust_build ito_generate_risk_interface)

add_custom_target(ito_benchmark
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/scripts/benchmark_multibranch.py --output ${CMAKE_CURRENT_SOURCE_DIR}/docs/benchmarks/multibranch_benchmark.json
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/scripts/render_benchmark_report.py ${CMAKE_CURRENT_SOURCE_DIR}/docs/benchmarks/multibranch_benchmark.json ${CMAKE_CURRENT_SOURCE_DIR}/docs/benchmarks
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(ito_python_test ALL
    COMMAND ${CMAKE_COMMAND} -E env PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/python/replay:${CMAKE_CURRENT_SOURCE_DIR}/python/ops_tools python3 -m unittest discover -s ${CMAKE_CURRENT_SOURCE_DIR}/tests/python
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
