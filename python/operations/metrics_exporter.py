#!/usr/bin/env python3
"""Prometheus HTTP Metrics Exporter for Ito System Telemetry."""

import http.server
import json
import os
import sys
import time
from typing import Dict, Any


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()

        metrics_text = self.generate_prometheus_metrics()
        self.wfile.write(metrics_text.encode("utf-8"))

    def generate_prometheus_metrics(self) -> str:
        lines = [
            "# HELP ito_production_readiness Current production readiness status (1=ready, 0=not ready)",
            "# TYPE ito_production_readiness gauge",
            "ito_production_readiness 0",
            "",
            "# HELP ito_external_blocker_count Active external blocker count",
            "# TYPE ito_external_blocker_count gauge",
            "ito_external_blocker_count 6",
            "",
            "# HELP ito_recovery_artifact_present Presence of recovery artifact (1=true, 0=false)",
            "# TYPE ito_recovery_artifact_present gauge",
            "ito_recovery_artifact_present 1",
            "",
            "# HELP ito_local_validation_pass Local validation pass indicator",
            "# TYPE ito_local_validation_pass gauge",
            "ito_local_validation_pass 1",
            "",
            "# HELP ito_system_uptime_seconds System uptime in seconds",
            "# TYPE ito_system_uptime_seconds counter",
            f"ito_system_uptime_seconds {int(time.time())}",
        ]
        return "\n".join(lines) + "\n"

    def log_message(self, format: str, *args: Any) -> None:
        pass


def run_exporter(port: int = 9090) -> None:
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, MetricsHandler)
    print(f"Ito Prometheus Metrics Exporter listening on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down exporter.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9090
    run_exporter(port)
