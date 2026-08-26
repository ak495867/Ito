import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2] / "python" / "replay"))
sys.path.insert(0, str(Path(__file__).parents[2] / "python" / "ops_tools"))

from replay import Event, validate
from health import HealthSnapshot


class ItoTests(unittest.TestCase):
    def test_contiguous_events_are_valid(self):
        events = [Event(1, 1, "intent", 10, "x"), Event(2, 2, "risk", 10, "approved")]
        self.assertEqual(validate(events), [])

    def test_sequence_gap_is_detected(self):
        events = [Event(1, 1, "intent", 10, "x"), Event(3, 3, "risk", 10, "approved")]
        self.assertEqual(validate(events), ["sequence_gap:2:3"])

    def test_health_is_fail_closed(self):
        snapshot = HealthSnapshot("branch-ny", True, False, True, True, True)
        self.assertFalse(snapshot.trading_allowed)

    def test_health_allows_ready_branch(self):
        snapshot = HealthSnapshot("branch-ny", True, True, True, True, True)
        self.assertTrue(snapshot.trading_allowed)


if __name__ == "__main__":
    unittest.main()
