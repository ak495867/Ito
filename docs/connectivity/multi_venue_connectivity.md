# Ito Multi-Venue Connectivity

## Purpose

Ito uses a normalized internal order and execution model so that strategies, risk controls, routing, reconciliation, and evidence services do not depend directly on a broker or exchange wire protocol. Venue adapters translate between the normalized model and the approved external session.

## Supported adapter families

| Adapter family | Intended use | Live state |
| --- | --- | --- |
| Simulator | Deterministic matching and integration tests | Enabled for local simulation |
| Binary venue adapter | Exchange-native binary order entry and market data | Interface-ready, disabled by default |
| FIX venue adapter | Broker and exchange FIX sessions | Interface-ready, disabled by default |
| REST adapter | Administrative, reference-data, and non-latency-sensitive workflows | Interface-ready, disabled by default |
| WebSocket adapter | Streaming broker or venue control and market-data workflows | Interface-ready, disabled by default |

A production adapter must implement authentication, message encoding, heartbeat, sequence recovery, throttling, venue-specific order state, error mapping, cancel-on-disconnect behavior, and certification evidence. The current network adapter provides a controlled TCP boundary and normalized framing foundation; it deliberately refuses live TLS-required sessions until a certified transport implementation is supplied.

## Session ownership

Every venue session has a branch scope, legal-entity scope, venue identity, broker identity, session epoch, lease owner, heartbeat, rate limit, and live-enable flag. Only the fenced lease owner may originate live order messages. A session in `Uncertain`, `Degraded`, `Halted`, or expired-lease state cannot originate new orders.

## Routing

The smart-order router filters candidates by enabled state, available quantity, fee, price validity, policy limits, and session readiness. It ranks the remaining candidates using configured rank, fee, and venue identifier. If the first venue is unavailable, the router may use a configured broker or exchange fallback only when the policy allows it. An ambiguous order blocks retry until venue reconciliation completes.

## Connectivity lifecycle

```text
DISABLED
   -> CONNECTING
   -> READY
   -> DEGRADED
   -> RECOVERY
   -> READY
   -> HALTED
   -> DISABLED
```

A transition is recorded in the event journal. `READY` requires authenticated identity, compatible release, valid policy, healthy clock, healthy feed, active venue session, durable journal, and a valid session lease.

## Order lifecycle boundary

The strategy emits a normalized order intent. The local risk engine authorizes the intent. The router selects a session. The adapter encodes a venue-specific request. The adapter reports transport acceptance separately from venue acknowledgment. Execution reports are normalized and retained with correlation identifiers, venue sequence, exchange timestamp, receive timestamp, policy version, and adapter identity.

## Failover

Failover is explicit and fenced. The old owner is marked inactive, the replacement obtains a new lease epoch, venue status is queried, local working orders are reconciled, ambiguous orders are isolated, and only then can new order entry be enabled. The router cannot silently convert a rejected or uncertain order into a new venue submission.

## Configuration

The canonical connection profiles are under `config/exchanges` and `config/brokers`. The route policy is under `config/routing/default_routes.json`. All profiles are simulator-only or live-disabled in the repository. Production activation requires credential injection, transport certification, venue certification, independent risk approval, and operational sign-off.
