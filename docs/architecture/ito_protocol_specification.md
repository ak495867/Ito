# Ito Multi-Branch Communication Protocol Specification

**Protocol name:** Ito Branch Communication Protocol  
**Protocol identifier:** `ITO-BCP`  
**Version:** 1.0  
**Status:** Internal architecture and simulator specification  
**Transport model:** Reliable authenticated control channels; deterministic local execution channels; append-only evidence streams

## 1. Purpose and boundary

ITO-BCP carries authenticated control, policy, risk, execution-state, operational-health, evidence, and recovery messages between Ito's central control domain, branch control planes, branch execution hosts, FPGA edge devices, and approved venue adapters.

ITO-BCP is not a replacement for an exchange-native protocol. A venue adapter translates between ITO-BCP execution intents and the venue or broker's certified order-entry protocol. Ito's internal protocol preserves branch, legal entity, strategy, policy, timing, and evidence context that an external venue protocol may not carry.

The protocol has a strict boundary between **control messages** and **execution messages**. Control messages may use a reliable stream transport and a general-purpose serialization format. Execution messages use a fixed-layout binary representation at the host-to-FPGA boundary. Both representations share the same semantic identifiers, sequence rules, and authorization model.

## 2. Design goals

| Goal | Protocol requirement |
| --- | --- |
| Branch isolation | Every message carries a branch and legal-entity scope; receivers reject mismatched scope |
| Authenticity | Every inter-node session uses mutual machine authentication; high-impact frames are signed |
| Integrity | Header, payload, sequence, and policy context are integrity-protected |
| Replay resistance | Session epochs, monotonic sequences, expirations, and nonce or identifier uniqueness are enforced |
| Determinism | Execution frames have bounded size, bounded parsing work, and explicit error outcomes |
| Safe degradation | A branch can use a valid cached policy snapshot but cannot widen its approved envelope |
| Auditability | Every accepted, rejected, expired, or malformed frame produces an evidence event |
| Compatibility | Major and minor protocol versions and schema hashes are negotiated explicitly |
| Recovery | Sequence gaps and ambiguous state enter recovery rather than blind retry |
| Availability | Halt and cancel messages have priority and independent local enforcement |

## 3. Participants and trust roles

| Role | Identifier | Responsibilities |
| --- | --- | --- |
| Group control | `GROUP` | Publishes signed policy, limits, releases, branch authority, and group halt state |
| Branch gateway | `BRANCH_GATEWAY` | Terminates central sessions, validates scope, distributes state, and forwards evidence |
| Branch control plane | `BRANCH_CONTROL` | Owns local policy cache, operations state, local risk snapshot, and session supervision |
| Execution host | `EXEC_HOST` | Runs C++ strategy and execution components; emits intents and consumes decisions |
| FPGA edge | `FPGA_EDGE` | Processes deterministic market-data and order frames; enforces local safety gates |
| Venue adapter | `VENUE_ADAPTER` | Converts approved execution frames into venue-native traffic and reports state |
| Evidence service | `EVIDENCE` | Stores ordered records, integrity checkpoints, archive references, and retention metadata |
| Operations agent | `OPS_AGENT` | Publishes health, clock, hardware, software, and service state |
| Recovery coordinator | `RECOVERY` | Coordinates sequence recovery, failover fencing, and reconciliation |

A participant is identified by a stable logical identity and a device or workload identity. Hostnames, IP addresses, and process identifiers are attributes, not trust anchors.

## 4. Channel classes

| Channel | Direction | Typical transport | Reliability | Priority | Data examples |
| --- | --- | --- | --- | --- | --- |
| `CONTROL` | Group to branch and branch to group | Authenticated reliable stream | Durable and ordered | High | Policy, limits, release, branch mode |
| `RISK` | Branch control to execution edge | Local bounded IPC or shared memory | Ordered and fail-closed | Critical | Limit snapshots, halt state, risk decisions |
| `MARKET_DATA` | Venue to branch edge | Multicast or direct feed | Sequence-recoverable | Critical | Quotes, trades, depth, status |
| `EXECUTION` | Branch edge to venue adapter | Dedicated low-latency path | Ordered and stateful | Critical | New, cancel, replace, status |
| `ACK` | Venue adapter to branch edge | Dedicated low-latency path | Ordered and stateful | Critical | Accepted, rejected, filled, cancelled |
| `EVIDENCE` | Branch to central archive | Reliable batched stream | Append-preserving | High | Orders, decisions, config, telemetry |
| `OPS` | Agent to branch control | Authenticated reliable stream | Best effort with local buffer | Medium | Health, metrics, alerts |
| `RECOVERY` | Branch and venue adapter | Authenticated reliable stream | Ordered and idempotent | Critical | Session recovery and reconciliation |
| `BRANCH_MESH` | Branch to branch through central relay | Authenticated reliable stream | Ordered by logical topic | High | Consolidated exposure and halt state |

Control, risk, execution, and acknowledgment channels must not share an unbounded queue. The halt and cancel paths have reserved capacity.

## 5. Common frame envelope

Every protocol frame has the following logical header. A binary execution header uses fixed-width fields in the same order; a control message maps these fields to a versioned schema.

| Field | Width or type | Requirement |
| --- | --- | --- |
| `magic` | 16 bits | Constant protocol marker |
| `major_version` | 8 bits | Incompatible wire changes increment this value |
| `minor_version` | 8 bits | Backward-compatible additions increment this value |
| `message_type` | 16 bits | Enumerated semantic message type |
| `channel` | 8 bits | Channel class |
| `flags` | 8 bits | Signed, urgent, replayable, compressed, or recovery flags |
| `header_length` | 16 bits | Exact serialized header size |
| `payload_length` | 32 bits | Bounded by channel-specific maximum |
| `session_epoch` | 64 bits | Changes on session establishment or controlled recovery |
| `frame_sequence` | 64 bits | Monotonic within session and channel |
| `event_id` | 64 bits | Unique event identifier |
| `correlation_id` | 64 bits | End-to-end request or order chain |
| `causation_id` | 64 bits | Directly originating event, zero when not applicable |
| `branch_id` | 64 bits | Branch scope |
| `entity_id` | 64 bits | Legal entity or fund scope |
| `strategy_id` | 64 bits | Strategy scope, zero for control messages |
| `deployment_id` | 64 bits | Exact software and FPGA deployment scope |
| `policy_version` | 64 bits | Limit or governance snapshot used |
| `created_ns` | 64 bits | Origin timestamp |
| `expires_ns` | 64 bits | Hard expiration; zero only for non-expiring archive metadata |
| `payload_hash` | 256 bits | Digest of canonical payload bytes |
| `signature` | Variable | Required for high-impact control and risk messages |
| `payload` | Bounded bytes | Canonical message body |

The receiver validates lengths before allocating or parsing. Unknown message types are rejected unless the channel explicitly permits forward-compatible preservation. Unknown fields are permitted only in control schemas that declare this behavior.

## 6. Message taxonomy

| Code | Message | Sender | Receiver | Effect |
| ---: | --- | --- | --- | --- |
| 1 | `HELLO` | Any | Session peer | Negotiates version, identity, capabilities, and clock domain |
| 2 | `WELCOME` | Session peer | Any | Confirms authenticated session and epoch |
| 10 | `POLICY_SNAPSHOT` | Group | Branch | Replaces or tightens cached policy |
| 11 | `LIMIT_SNAPSHOT` | Group or branch risk | Risk and FPGA edge | Atomically activates a limit set |
| 12 | `BRANCH_MODE` | Group or branch | Branch components | Normal, degraded, restricted, or halted state |
| 13 | `RELEASE_MANIFEST` | Release service | Branch gateway | Authorizes artifact and compatibility set |
| 20 | `MARKET_EVENT` | Venue edge | Strategy and journal | Normalized market data |
| 21 | `FEED_HEALTH` | Venue edge | Risk and branch control | Feed sequence and quality state |
| 30 | `ORDER_INTENT` | Strategy or operator | Risk gate | Proposed order, never a venue command |
| 31 | `RISK_DECISION` | Risk gate | Strategy, edge, journal | Approved or rejected decision with reason |
| 32 | `ORDER_NEW` | FPGA edge | Venue adapter | Approved new order |
| 33 | `ORDER_CANCEL` | FPGA edge | Venue adapter | Approved cancel or emergency cancel |
| 34 | `ORDER_REPLACE` | FPGA edge | Venue adapter | Approved replace |
| 35 | `ORDER_ACK` | Venue adapter | FPGA edge and journal | Venue acknowledgment or rejection |
| 36 | `FILL` | Venue adapter | Portfolio and journal | Execution fill or correction |
| 40 | `POSITION_SNAPSHOT` | Portfolio risk | Branch and group | Position and exposure state |
| 41 | `EXPOSURE_UPDATE` | Branch risk | Group risk | Consolidated exposure update |
| 50 | `HEALTH_STATUS` | Operations agent | Branch and group | Host, FPGA, service, and clock state |
| 51 | `CLOCK_STATUS` | Timing agent | Risk and journal | Offset, holdover, and health state |
| 60 | `SEQUENCE_GAP` | Receiver | Session peer | Gap declaration and recovery request |
| 61 | `RECOVERY_STATUS` | Session peer | Receiver | Recovery progress and result |
| 70 | `HALT` | Group, branch, or FPGA | All relevant components | Blocks new order entry and enables cancellation |
| 71 | `HALT_CLEAR_REQUEST` | Operator | Risk and group | Requests controlled restart |
| 72 | `HALT_CLEAR` | Authorized authority | Branch and edge | Clears halt after health validation |
| 80 | `EVIDENCE_BATCH` | Branch | Evidence archive | Ordered batch of evidence events |
| 81 | `EVIDENCE_CHECKPOINT` | Branch | Evidence archive | Integrity checkpoint and replication state |

## 7. Canonical order-intent body

The order-intent body uses the same semantic fields as `interfaces/schemas/order_intent.schema.json`.

| Field | Type | Validation |
| --- | --- | --- |
| `instrument_id` | Unsigned integer | Must be active in branch reference data |
| `venue_id` | Unsigned integer | Must be enabled for branch and strategy |
| `account_id` | Unsigned integer | Must be entitled to strategy and instrument |
| `side` | Enum | `buy` or `sell` |
| `order_type` | Enum | `limit` or explicitly enabled type |
| `time_in_force` | Enum | Venue and strategy compatible |
| `price_ticks` | Signed integer | Positive, scale defined by instrument |
| `quantity` | Signed integer | Positive and within policy |
| `strategy_reason` | Enumerated code | Required for automated strategies |
| `market_view_sequence` | Unsigned integer | Identifies market state used |
| `state_hash` | 256-bit digest | Identifies relevant strategy state |

An order intent is not accepted merely because its body is well-formed. The risk gate validates identity, branch mode, policy freshness, feed health, clock health, venue status, rate limits, notional, position, and account permissions.

## 8. Session establishment

A session starts with transport connection, machine identity authentication, `HELLO`, capability negotiation, `WELCOME`, and a fresh session epoch. The peer records the certificate or device identity, protocol version, branch scope, channel scope, clock domain, and last accepted sequence.

The session does not become execution-ready until the receiver has verified the active release manifest, limit snapshot, branch mode, clock health, feed health, journal health, and venue session state. Control sessions may remain available while execution sessions are restricted.

Session keys are rotated according to the organization's key-management policy. A session epoch change invalidates frames from an earlier epoch unless the recovery procedure explicitly authorizes an archival or replay operation.

## 9. Sequence and replay rules

Every channel has a monotonic frame sequence. A receiver accepts the next expected sequence, records a duplicate as an evidence event, and declares a gap when a higher sequence arrives. A gap on market data invalidates dependent book state; a gap on risk or execution control invalidates the affected authorization path.

A frame is rejected when its session epoch is unknown, sequence is outside the recovery window, creation time is outside permitted clock tolerance, expiration has passed, payload hash does not match, signature is invalid, branch scope does not match, or policy version is not acceptable.

Messages are idempotent only when their semantic definition explicitly says so. `LIMIT_SNAPSHOT`, `HALT`, and `HALT_CLEAR` are versioned state transitions. `ORDER_NEW` is not blindly idempotent; its client order identifier must be reconciled with the venue before any retry or recovery action.

## 10. Control and policy flow

1. Group control creates a policy or limit artifact.
2. The artifact is validated by policy and configuration validators.
3. The artifact is signed and assigned a version and expiration.
4. The branch gateway authenticates the sender and validates the scope.
5. The branch stores the artifact durably and verifies its signature.
6. The branch control plane distributes it atomically to risk and FPGA edge components.
7. Each component acknowledges the version and its effective state.
8. The branch reports activation evidence to the group.
9. New orders use only an acknowledged, unexpired snapshot.
10. A partial distribution results in restricted mode rather than a mixed policy state.

A branch may publish a tighter local limit, but a local process cannot widen a group-approved limit without a new authorized artifact.

## 11. Market-data flow

1. Venue packets arrive at the branch FPGA edge.
2. The edge captures a hardware timestamp and validates the source and packet structure.
3. The sequence guard checks continuity, duplicate state, and gap state.
4. The decoder converts the venue message into a normalized event.
5. The book builder updates bounded local state.
6. The edge emits `MARKET_EVENT` and `FEED_HEALTH` records.
7. The strategy runtime consumes an immutable view associated with a market sequence.
8. The event and raw-packet reference enter the local journal.
9. The evidence buffer forwards the event when the evidence channel is available.

A feed gap, stale feed, crossed state, or invalid timestamp causes dependent strategies to be restricted according to the branch policy.

## 12. Order flow

1. A strategy or authorized operator creates `ORDER_INTENT`.
2. The intent is assigned an event and correlation identifier.
3. The risk gate validates the intent against the latest acknowledged snapshot.
4. The risk gate emits `RISK_DECISION` with rule, snapshot, and reason metadata.
5. An approved intent enters the FPGA order sequencer.
6. The sequencer assigns a client order identifier and emits an execution frame.
7. The venue adapter validates the frame and translates it to venue-native order entry.
8. The venue response is captured with receive timestamps and session sequence.
9. Acknowledgments, rejects, fills, and corrections enter the journal.
10. Portfolio and reconciliation services update positions and evidence.

A rejected risk decision never reaches the venue adapter. An uncertain venue result enters recovery and cannot be resolved by blind resubmission.

## 13. Halt flow

A halt may originate from group control, branch operations, risk, FPGA health, clock health, feed health, venue status, or an independent physical input. The local FPGA kill path blocks new orders and permits configured cancellation behavior immediately. The branch gateway distributes the halt to other relevant components and records the source, reason, scope, and time.

Clearing a halt requires a new `HALT_CLEAR_REQUEST`, health verification, valid policy and limit snapshots, stable sessions, evidence readiness, and approvals appropriate to scope. A clear command is itself signed and versioned. The system must not infer that a lost halt message means that the halt has been cleared.

## 14. Failover and recovery flow

1. The active component declares a fault or loses an expected lease.
2. The standby remains fenced from originating live orders.
3. The recovery coordinator identifies the last durable event and last acknowledged venue state.
4. The system creates a new session epoch or recovers the venue session as permitted.
5. The venue adapter requests order status and sequence recovery.
6. Local working orders and fills are reconciled against venue state.
7. The branch risk snapshot and journal replication are checked.
8. A controlled promotion is recorded with operator and policy authority.
9. New order entry is enabled only after all readiness conditions pass.
10. The incident remains open until evidence and root-cause review are complete.

Split-brain protection is mandatory. Only one fenced owner may originate orders for a logical venue session.

## 15. Error taxonomy

| Code | Error | Required receiver action |
| ---: | --- | --- |
| 100 | `VERSION_UNSUPPORTED` | Reject and negotiate supported version |
| 101 | `IDENTITY_INVALID` | Close session and raise security evidence |
| 102 | `SCOPE_MISMATCH` | Reject, isolate message source, alert operations |
| 103 | `PAYLOAD_INVALID` | Reject and count malformed input |
| 104 | `SIGNATURE_INVALID` | Reject, invalidate artifact, raise security incident |
| 105 | `POLICY_EXPIRED` | Enter restricted mode for dependent actions |
| 106 | `SEQUENCE_GAP` | Pause affected flow and start recovery |
| 107 | `DUPLICATE_FRAME` | Ignore semantic effect and record evidence |
| 108 | `CLOCK_UNHEALTHY` | Reject new order entry and preserve evidence |
| 109 | `FEED_UNHEALTHY` | Reject dependent order intents |
| 110 | `JOURNAL_UNAVAILABLE` | Restrict or halt according to policy |
| 111 | `VENUE_UNCERTAIN` | Enter recovery; never blind retry |
| 112 | `FENCING_FAILURE` | Halt order origin and escalate critical incident |
| 113 | `LIMIT_BREACH` | Reject order and record rule decision |
| 114 | `HALTED` | Reject new orders and follow halt procedure |

## 16. Performance and capacity contracts

The execution envelope is bounded by message sizes, queue depth, rate limits, and reserved capacity.

| Contract | Initial engineering target |
| --- | ---: |
| Maximum execution frame payload | 256 bytes |
| Maximum control frame payload | 1 MiB |
| Reserved halt/cancel queue | 25% of execution queue capacity |
| Risk snapshot activation | Atomic at a sequence boundary |
| Local risk decision | No network round trip to central control |
| Evidence append | No silent discard; backpressure produces health transition |
| Control-policy propagation | Sub-second target in normal branch conditions |
| Clock-health evaluation | Continuous with explicit stale and holdover state |

Targets are measured in the actual deployment topology and are not venue guarantees.

## 17. Compatibility and rollout

A receiver advertises supported major and minor versions, maximum payload sizes, message types, channel classes, and schema hashes. New minor-version fields are added only with defined default behavior. Major-version changes require a parallel deployment and explicit cutover.

Protocol rollout occurs through development, simulator, FPGA laboratory, venue certification, branch shadow, canary, and production stages. Each stage records the exact binary, RTL, schema, policy, and deployment manifest.

## 18. Evidence requirements

The journal records the raw frame reference, canonical payload hash, session epoch, sequence, identity, branch scope, policy version, clock state, validation outcome, and downstream event references. For an order, the evidence chain must connect market-data sequence, strategy state, order intent, risk decision, execution frame, venue response, fill, position update, and reconciliation result.

## 19. Security requirements

Transport sessions use mutually authenticated machine identity. Critical messages use digital signatures or an equivalent protected signing mechanism. Keys are not embedded in binaries or source files. Branch gateways enforce scope, expiry, signature, sequence, and authorization checks before forwarding a frame.

Protocol parsers are fuzzed with malformed lengths, invalid enums, truncated bodies, duplicate fields, oversized payloads, sequence resets, stale timestamps, invalid signatures, and scope mismatch. A parser failure must not crash the execution host or produce an order.

## 20. Implementation mapping

| Specification area | Repository implementation |
| --- | --- |
| Semantic order contract | `interfaces/schemas/ito_protocol.hpp` and `interfaces/schemas/order_intent.schema.json` |
| Risk register map | `interfaces/register_maps/risk_gate.json` |
| C++ event ordering | `cpp/ito_core` |
| C++ risk gate | `cpp/ito_risk` |
| C++ execution state | `cpp/ito_execution` |
| FPGA risk gate | `rtl/risk_gate/pre_trade_gate.sv` |
| FPGA order sequencing | `rtl/order_sequencer/order_sequencer.sv` |
| FPGA emergency stop | `rtl/kill_switch/kill_switch.sv` |
| Cross-language validation | `tests` and `scripts/build_all.sh` |

## 21. Acceptance tests

The protocol implementation is acceptable for the simulator stage when it can demonstrate authenticated or test-authenticated session establishment, version rejection, scope rejection, sequence-gap detection, duplicate suppression, expiration rejection, policy activation, risk rejection, approved order forwarding, venue acknowledgment, ambiguous-state recovery, halt propagation, halt clearing, evidence ordering, and branch isolation.
