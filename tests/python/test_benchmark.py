import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from benchmark_multibranch import branch_samples, summarize


class BenchmarkTests(unittest.TestCase):
    def test_seeded_samples_are_deterministic(self):
        import random
        first = branch_samples("branch-01", 10, 1000, 25000, 5000, random.Random(7))
        second = branch_samples("branch-01", 10, 1000, 25000, 5000, random.Random(7))
        self.assertEqual(first, second)

    def test_summary_contains_each_branch(self):
        import random
        samples = branch_samples("branch-01", 10, 1000, 25000, 5000, random.Random(7)) + branch_samples("branch-02", 10, 1000, 25000, 5000, random.Random(8))
        result = summarize(samples, 0.01, "exchange_simulator_pass")
        self.assertEqual(result["branches"], 2)
        self.assertEqual(result["messages"], 20)
        self.assertEqual(result["exchange_simulator"], "exchange_simulator_pass")
        self.assertGreater(result["throughput_messages_per_second"], 0)


if __name__ == "__main__":
    unittest.main()
