import tempfile
import unittest
from pathlib import Path

from interfaces.custody.key_store import HmacSimulatorSigner, InMemoryKeyStore
from interfaces.deployment.release import (
    DeploymentEnvironment,
    DryRunDeploymentProvider,
    Release,
)
from interfaces.fpga.evidence import FrameEvidence, TimingEvidence
from interfaces.recovery.checkpoint_store import SQLiteCheckpointStore
from interfaces.recovery.lease_store import InMemoryLeaseStore
from interfaces.venue.drop_copy import ExecutionReport, SimulatedDropCopyFeed
from interfaces.venue.market_data import Quote, SimulatedMarketDataFeed
from interfaces.venue.order_gateway import (
    Environment,
    OrderRequest,
    OrderSide,
    OrderState,
    SimulatedOrderGateway,
)


class InterfaceTests(unittest.TestCase):
    def test_order_gateway_rejects_live_and_duplicates(self):
        gateway = SimulatedOrderGateway(7)
        request = OrderRequest(1, "ABC", OrderSide.BUY, 5, 100)
        self.assertEqual(gateway.submit(request).state, OrderState.ACCEPTED)
        self.assertEqual(gateway.submit(request).state, OrderState.REJECTED)
        with self.assertRaises(ValueError):
            gateway.submit(
                OrderRequest(2, "ABC", OrderSide.BUY, 1, 100, Environment.LIVE)
            )

    def test_order_gateway_cancel_is_idempotent_for_missing_orders(self):
        gateway = SimulatedOrderGateway(7)
        self.assertEqual(gateway.cancel(1).state, OrderState.UNKNOWN)
        gateway.submit(OrderRequest(1, "ABC", OrderSide.BUY, 5, 100))
        self.assertEqual(gateway.cancel(1).state, OrderState.CANCELED)

    def test_market_data_rejects_duplicate_sequences(self):
        quote = Quote("ABC", 1, 100, 99, 100)
        with self.assertRaises(ValueError):
            SimulatedMarketDataFeed([quote, quote])

    def test_drop_copy_rejects_duplicate_execution_ids(self):
        report = ExecutionReport("exec-1", 1, "ABC", OrderSide.BUY, 1, 100, 100)
        with self.assertRaises(ValueError):
            SimulatedDropCopyFeed([report, report])

    def test_signer_rotates_and_verifies(self):
        store = InMemoryKeyStore()
        signer = HmacSimulatorSigner(store)
        payload = b"policy"
        signature = signer.sign("risk", payload)
        self.assertTrue(signer.verify("risk", payload, signature))
        store.rotate("risk")
        self.assertTrue(signer.verify("risk", payload, signature))
        self.assertFalse(signer.verify("risk", b"other", signature))

    def test_lease_store_uses_fencing_tokens(self):
        store = InMemoryLeaseStore()
        first = store.acquire("execution", "node-a", 10, 100)
        self.assertIsNotNone(first)
        self.assertIsNone(store.acquire("execution", "node-b", 20, 100))
        expired = store.acquire("execution", "node-b", 110, 100)
        self.assertIsNotNone(expired)
        self.assertGreater(expired.fencing_token, first.fencing_token)
        self.assertIsNone(store.renew(first, 110, 100))

    def test_checkpoint_store_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoints.db"
            with SQLiteCheckpointStore(path) as store:
                saved = store.save("risk", 4, {"approved": 3})
                loaded = store.load("risk")
                self.assertEqual(loaded, saved)
                store.connection.execute(
                    "UPDATE checkpoints SET payload = ? WHERE name = ?",
                    ('{"approved":4}', "risk"),
                )
                store.connection.commit()
                with self.assertRaises(ValueError):
                    store.load("risk")

    def test_fpga_evidence_requires_safety_checks(self):
        timing = TimingEvidence(250_000_000, 4, 120, True, True)
        evidence = FrameEvidence.create("risk-frame-v1", b"frame", timing)
        evidence.validate()
        with self.assertRaises(ValueError):
            FrameEvidence.create(
                "risk-frame-v1", b"frame", TimingEvidence(1, 1, 0, False, True)
            )

    def test_deployment_is_dry_run_and_non_production(self):
        provider = DryRunDeploymentProvider()
        release = Release("r1", "a" * 64, 3, DeploymentEnvironment.STAGING)
        self.assertEqual(provider.deploy(release), "dry-run-deployed:r1")
        production = Release("r2", "b" * 64, 3, DeploymentEnvironment.PRODUCTION)
        with self.assertRaises(ValueError):
            provider.deploy(production)


if __name__ == "__main__":
    unittest.main()
