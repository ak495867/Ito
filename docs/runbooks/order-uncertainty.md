# Order uncertainty runbook

## Trigger

Use this runbook when a venue acknowledgment, rejection, cancel response, or session state is unknown after a network or gateway fault.

## Immediate actions

Place the affected gateway and strategy into restricted mode. Preserve raw packets, host telemetry, FPGA counters, session sequence state, deployment identity, and the relevant event-journal segment. Do not retry the original order blindly.

## Recovery sequence

Confirm the local event sequence, client order identifier, venue session identity, and last confirmed venue sequence. Reconnect only through the approved session-recovery procedure. Request venue-supported order status or recovery data. Reconcile working orders, fills, cancels, and rejects against the local journal. Mark the order as resolved only after an authoritative venue response and local event record agree.

## Exit criteria

The gateway may return to ready state only after the venue session is stable, the risk snapshot is valid, journal replication is healthy, no duplicate order is suspected, and operations and risk owners approve the transition. The incident remains open until root cause and evidence preservation are complete.
