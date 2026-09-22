from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ExporterError(ValueError):
    pass


def load_snapshot(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExporterError(f"snapshot_invalid:{error}") from error
    if not isinstance(value, dict):
        raise ExporterError("snapshot_invalid")
    return value


def render_audit_metrics(audit: list[dict[str, object]] | None) -> str:
    if audit is None:
        return ""
    
    actions_count: dict[str, int] = {}
    total_actions = 0
    
    for entry in audit:
        if isinstance(entry, dict):
            action = entry.get("action")
            if isinstance(action, str):
                actions_count[action] = actions_count.get(action, 0) + 1
                total_actions += 1
    
    rows = [
        "# TYPE ito_audit_total_events gauge",
        f"ito_audit_total_events {total_actions}",
    ]
    
    for action, count in sorted(actions_count.items()):
        metric_name = f"ito_audit_action_{action.replace('-', '_')}_total"
        rows.extend([
            f"# TYPE {metric_name} gauge",
            f"{metric_name} {count}",
        ])
    
    return "\n".join(rows) + "\n"


def render_metrics(
    health: dict[str, object], 
    portfolio: dict[str, object] | None = None,
    audit: list[dict[str, object]] | None = None
) -> str:
    local = 1 if health.get("local_status") == "healthy" else 0
    production = 1 if health.get("production_status") == "production_ready" else 0
    recovery = 1 if health.get("recovery_artifact_present") is True else 0
    blockers = health.get("external_blocker_count", 0)
    if not isinstance(blockers, int) or blockers < 0:
        raise ExporterError("blocker_count_invalid")
    rows = [
        "# TYPE ito_local_validation_pass gauge",
        f"ito_local_validation_pass {local}",
        "# TYPE ito_production_readiness gauge",
        f"ito_production_readiness {production}",
        "# TYPE ito_external_blocker_count gauge",
        f"ito_external_blocker_count {blockers}",
        "# TYPE ito_recovery_artifact_present gauge",
        f"ito_recovery_artifact_present {recovery}",
    ]
    if portfolio is not None:
        numeric = {
            "ito_portfolio_net_position": portfolio.get("net_position"),
            "ito_portfolio_gross_position": portfolio.get("gross_position"),
            "ito_portfolio_gross_notional_ticks": portfolio.get("gross_notional_ticks"),
            "ito_portfolio_realized_pnl_ticks": portfolio.get("realized_pnl_ticks"),
            "ito_portfolio_unrealized_pnl_ticks": portfolio.get("unrealized_pnl_ticks"),
            "ito_portfolio_loss_ticks": portfolio.get("loss_ticks"),
        }
        for name, value in numeric.items():
            if not isinstance(value, int):
                raise ExporterError(f"metric_invalid:{name}")
            rows.extend(("# TYPE " + name + " gauge", f"{name} {value}"))
    
    if audit is not None:
        rows.append(render_audit_metrics(audit))
    
    return "\n".join(rows) + "\n"


def make_handler(health_path: Path, portfolio_path: Path | None, audit_path: Path | None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_response(404)
                self.end_headers()
                return
            try:
                health = load_snapshot(health_path)
                portfolio = (
                    load_snapshot(portfolio_path)
                    if portfolio_path is not None and portfolio_path.is_file()
                    else None
                )
                audit = (
                    load_snapshot(audit_path)
                    if audit_path is not None and audit_path.is_file()
                    else None
                )
                payload = render_metrics(health, portfolio, audit).encode("utf-8")
            except ExporterError:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", type=Path, required=True)
    parser.add_argument("--portfolio", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--listen", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9108)
    args = parser.parse_args()
    if args.listen:
        ThreadingHTTPServer(
            (args.host, args.port), make_handler(args.health, args.portfolio, args.audit)
        ).serve_forever()
    else:
        health = load_snapshot(args.health)
        portfolio = (
            load_snapshot(args.portfolio)
            if args.portfolio is not None and args.portfolio.is_file()
            else None
        )
        audit = (
            load_snapshot(args.audit)
            if args.audit is not None and args.audit.is_file()
            else None
        )
        output = render_metrics(health, portfolio, audit)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())