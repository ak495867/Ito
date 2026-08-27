import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "python" / "connectivity"))
sys.path.insert(0, str(Path(__file__).parents[2] / "python" / "reconciliation"))
sys.path.insert(0, str(Path(__file__).parents[2] / "python" / "operations"))

from config_linter import validate_profiles
from failover_drill import drill
from reconcile import compare
from venue_status import aggregate
from route_recommendation import recommend


class ConnectivityTests(unittest.TestCase):
    def test_profiles_are_valid(self):
        root = Path(__file__).parents[2]
        paths = [
            root / "config/exchanges/exchange-a-sim.json",
            root / "config/exchanges/exchange-b-sim.json",
            root / "config/brokers/broker-a-sim.json",
            root / "config/brokers/broker-b-sim.json",
        ]
        self.assertEqual(validate_profiles(paths), [])

    def test_reconciliation_blocks_mismatch(self):
        local = [
            {"client_order_id": 1, "executed_quantity": 10, "average_price_ticks": 100}
        ]
        venue = [
            {"client_order_id": 1, "executed_quantity": 5, "average_price_ticks": 100}
        ]
        findings = compare(local, venue)
        self.assertEqual(findings[0]["state"], "quantity_mismatch")

    def test_route_recommendation_filters_unready_venues(self):
        routes = [
            {
                "venue_id": 5,
                "rank": 1,
                "fee_bps": 2,
                "enabled": True,
                "live_enabled": False,
                "max_order_quantity": 100,
            },
            {
                "venue_id": 6,
                "rank": 2,
                "fee_bps": 3,
                "enabled": True,
                "live_enabled": False,
                "max_order_quantity": 100,
            },
        ]
        sessions = [
            {"venue_id": 5, "status": "degraded"},
            {"venue_id": 6, "status": "ready"},
        ]
        result = recommend(routes, sessions, 10)
        self.assertEqual([item["venue_id"] for item in result], [6])

    def test_venue_status_requires_all_sessions_ready(self):
        self.assertTrue(
            aggregate(
                [{"venue_id": 5, "status": "ready"}, {"venue_id": 6, "status": "ready"}]
            )["execution_enabled"]
        )
        self.assertFalse(
            aggregate(
                [
                    {"venue_id": 5, "status": "ready"},
                    {"venue_id": 6, "status": "uncertain"},
                ]
            )["execution_enabled"]
        )

    def test_failover_requires_clean_reconciliation(self):
        lease = {"owner_id": "node-a", "epoch": 2, "expires_at_ns": 1000, "now_ns": 500}
        self.assertFalse(drill(lease, [{"state": "missing_venue"}])["promoted"])
        self.assertTrue(drill(lease, [{"state": "matched"}])["promoted"])


if __name__ == "__main__":
    unittest.main()
