FROM ubuntu:24.04 AS builder

RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential cmake cargo rustc ocaml-nox ocaml-dune libyojson-ocaml-dev libssl-dev iverilog verilator python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ito
COPY . /opt/ito

RUN python3 scripts/generate_risk_interface.py \
    && cmake -S . -B build/cpp -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build/cpp \
    && cargo build --release --manifest-path rust/Cargo.toml \
    && dune build --root ocaml \
    && mkdir -p /opt/ito/bin \
    && cp build/cpp/ito_execution_host /opt/ito/bin/ \
    && cp build/cpp/ito_risk_engine /opt/ito/bin/ \
    && cp build/cpp/ito_branch_gateway /opt/ito/bin/ \
    && cp build/cpp/ito_operations_agent /opt/ito/bin/ \
    && cp build/cpp/ito_exchange_simulator /opt/ito/bin/ \
    && cp rust/target/release/ito-risk-service /opt/ito/bin/ \
    && cp rust/target/release/ito-connectivity-guard /opt/ito/bin/ \
    && cp rust/target/release/ito-policy-signer /opt/ito/bin/

FROM ubuntu:24.04

RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system ito && useradd --system --gid ito --home-dir /var/lib/ito --create-home ito \
    && mkdir -p /opt/ito/bin /var/lib/ito /var/log/ito \
    && chown -R ito:ito /opt/ito /var/lib/ito /var/log/ito

COPY --from=builder /opt/ito/bin /opt/ito/bin

USER ito:ito
WORKDIR /var/lib/ito
ENV ITO_MODE=restricted

CMD ["/opt/ito/bin/ito_operations_agent"]
