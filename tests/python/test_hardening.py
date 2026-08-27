import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

root = Path(__file__).parents[2]
sys.path.insert(0, str(root / "python" / "connectivity"))
sys.path.insert(0, str(root / "python" / "operations"))
sys.path.insert(0, str(root / "python" / "replay"))
sys.path.insert(0, str(root / "python" / "backtest"))
sys.path.insert(0, str(root / "python" / "portfolio"))
sys.path.insert(0, str(root / "scripts" / "operations"))

from backup_restore import BackupError, backup, restore
from durable_store import DurableEventStore, StoreError
from engine import Quote, ReplayBacktest, Signal
from health_report import build_report
from portfolio import Portfolio, PortfolioLimits
from prometheus_exporter import render_metrics
from production_gate_simulations import run as run_gate_simulations
from verify_release_binding import verify
from replay import Event, validate
from route_recommendation import recommend
from venue_status import aggregate


class HardeningTests(unittest.TestCase):
    def test_durable_store_survives_restart_and_verifies_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "events.sqlite"
            store = DurableEventStore(database)
            self.assertEqual(store.append(1, 10, "intent", 100, {"quantity": 2}), 1)
            store.write_snapshot("portfolio", {"net": 2})
            store.close()
            reopened = DurableEventStore(database)
            self.assertEqual(reopened.last_sequence(), 1)
            self.assertEqual(reopened.read_snapshot("portfolio")["payload"], {"net": 2})
            reopened.verify_recovery()
            with self.assertRaises(StoreError):
                reopened.append(1, 10, "duplicate", 101, {})
            reopened.close()

    def test_portfolio_tracks_realized_and_unrealized_pnl(self):
        portfolio = Portfolio(PortfolioLimits(100, 200, 100000, 60000, 10000))
        portfolio.apply_fill(7, 1, 10, 100)
        portfolio.apply_fill(7, -1, 4, 120)
        snapshot = portfolio.snapshot({7: 115})
        self.assertEqual(snapshot["realized_pnl_ticks"], 80)
        self.assertEqual(snapshot["unrealized_pnl_ticks"], 90)
        self.assertEqual(snapshot["net_position"], 6)

    def test_portfolio_rejects_projected_exposure(self):
        portfolio = Portfolio(PortfolioLimits(10, 10, 1000, 1000, 1000))
        portfolio.apply_fill(7, 1, 10, 100)
        self.assertEqual(
            portfolio.validate_order(7, 1, 1, 100), (False, "net_position_limit")
        )

    def test_portfolio_requires_explicit_short_permission(self):
        portfolio = Portfolio(PortfolioLimits(100, 200, 100000, 60000, 10000))
        self.assertEqual(
            portfolio.validate_order(7, -1, 1, 100), (False, "short_sale_disabled")
        )
        with self.assertRaises(ValueError):
            portfolio.apply_fill(7, -1, 1, 100)

    def test_six_external_gates_have_simulation_evidence(self):
        result = run_gate_simulations(root)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(len(result["limitations"]), 5)

    def test_prometheus_exporter_emits_allowlisted_metrics(self):
        health = {
            "local_status": "healthy",
            "production_status": "not_production_ready",
            "external_blocker_count": 6,
            "recovery_artifact_present": True,
        }
        portfolio = {
            "net_position": 4,
            "gross_position": 4,
            "gross_notional_ticks": 500,
            "realized_pnl_ticks": 20,
            "unrealized_pnl_ticks": -5,
            "loss_ticks": 0,
        }
        metrics = render_metrics(health, portfolio)
        self.assertIn("ito_portfolio_net_position 4", metrics)
        self.assertNotIn("__dict__", metrics)

    def test_live_route_requires_explicit_enablement(self):
        routes = [
            {
                "venue_id": 5,
                "rank": 1,
                "fee_bps": 2,
                "enabled": True,
                "max_order_quantity": 100,
            }
        ]
        sessions = [{"venue_id": 5, "status": "ready"}]
        self.assertEqual(recommend(routes, sessions, 10, live=True), [])

    def test_replay_rejects_duplicate_event_ids(self):
        events = [Event(1, 1, "intent", 1, "x"), Event(1, 2, "fill", 1, "y")]
        self.assertIn("duplicate_event_id:1", validate(events))

    def test_unknown_session_is_degraded(self):
        result = aggregate([{"venue_id": 5, "status": "unknown"}])
        self.assertEqual(result["degraded_count"], 1)
        self.assertFalse(result["execution_enabled"])

    def test_invalid_quote_does_not_fill(self):
        backtest = ReplayBacktest(100)
        quote = Quote(1, 101, 100)
        signal = Signal(1, 1, 10)
        self.assertIsNone(backtest.apply(quote, signal))

    def test_duplicate_quote_timestamp_is_rejected(self):
        backtest = ReplayBacktest(100)
        quotes = [Quote(1, 100, 101), Quote(1, 100, 101)]
        with self.assertRaises(ValueError):
            backtest.run(quotes, [])

    def test_local_health_report_separates_external_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            readiness = directory_path / "readiness.json"
            recovery = directory_path / "recovery.tar.gz"
            readiness.write_text(
                json.dumps(
                    {
                        "status": "not_production_ready",
                        "gates": [
                            {"id": "GATE-SW-001", "implemented": True},
                            {"id": "GATE-SEC-002", "implemented": False},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            recovery.write_bytes(b"recovery")
            result = build_report(readiness, recovery)
            self.assertEqual(result["local_status"], "healthy")
            self.assertEqual(result["external_blocker_count"], 1)

    def test_release_binding_recomputes_artifact_digests(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            policy = directory_path / "policy"
            rtl = directory_path / "rtl"
            schema = directory_path / "schema"
            for path, value in (
                (policy, b"policy"),
                (rtl, b"rtl"),
                (schema, b"schema"),
            ):
                path.write_bytes(value)
            binding = directory_path / "binding.json"
            binding.write_text(
                json.dumps(
                    {
                        "policy_version": 1,
                        "artifact_digest": hashlib.sha256(b"policy").hexdigest(),
                        "rtl_digest": hashlib.sha256(b"rtl").hexdigest(),
                        "schema_digest": hashlib.sha256(b"schema").hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            verify(binding, policy, rtl, schema)

    def test_backup_restore_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            restored = Path(directory) / "restored"
            archive = Path(directory) / "ito.tar.gz"
            selected = workspace / "config" / "risk"
            selected.mkdir(parents=True)
            source = selected / "policy.json"
            source.write_text('{"version":1}', encoding="utf-8")
            backup(workspace, archive, ["config/risk/policy.json"])
            restore(archive, restored)
            self.assertEqual(
                (restored / "config/risk/policy.json").read_text(encoding="utf-8"),
                '{"version":1}',
            )
            tampered_archive = Path(directory) / "tampered.tar.gz"
            with (
                tarfile.open(archive, "r:gz") as original,
                tarfile.open(tampered_archive, "w:gz") as tampered,
            ):
                manifest_member = original.getmember("manifest.json")
                manifest_payload = original.extractfile(manifest_member).read()
                tampered.addfile(manifest_member, io.BytesIO(manifest_payload))
                file_member = original.getmember("config/risk/policy.json")
                file_member.size = len(b'{"version":2}')
                tampered.addfile(file_member, io.BytesIO(b'{"version":2}'))
            with self.assertRaises(BackupError):
                restore(tampered_archive, restored / "tampered")


if __name__ == "__main__":
    unittest.main()
