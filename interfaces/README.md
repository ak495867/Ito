# Integration Interfaces

This directory contains stable contracts for venue execution, market data, drop-copy reconciliation, custody, checkpoint persistence, and fencing leases.

The included implementations are local simulators and are not production integrations. They provide deterministic behavior for tests and development while preserving production safety boundaries.

## Venue

`OrderGateway` accepts validated order requests and returns explicit acknowledgments. `SimulatedOrderGateway` rejects live execution, detects duplicate client order IDs, and models cancellation and unknown-order states.

`MarketDataFeed` validates quote identity, sequence, timestamps, and crossed prices. `DropCopyFeed` validates execution identity and rejects duplicate execution IDs.

A production provider must implement authentication, heartbeats, reconnect handling, sequence recovery, rate limits, cancel-on-disconnect behavior, and unknown execution handling.

## Custody

`KeyStore` models versioned, non-exportable keys. `Signer` provides signing and verification boundaries. `HmacSimulatorSigner` is only a deterministic local implementation and must be replaced with an HSM or KMS-backed provider before live use.

## Recovery

`CheckpointStore` provides integrity-hashed snapshots. `SQLiteCheckpointStore` is suitable for local development and evidence generation; production should use replicated durable storage.

`LeaseStore` provides fencing tokens so stale owners cannot renew or release a newer lease. `InMemoryLeaseStore` is a test implementation; production requires a consensus-backed coordination service.

## Production readiness boundary

No module in this directory enables live order submission, exports private key material, or claims production-grade failover. Real providers must be added behind these contracts and tested with cross-language contract vectors before any live deployment.
