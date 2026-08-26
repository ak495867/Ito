use ito_connectivity_guard::{authorize, lease_digest, SessionLease, SessionState, VenuePermission};
use std::env;

fn main() {
    let live = env::args().any(|value| value == "--live");
    let permission = VenuePermission { venue_id: 5, broker_id: 8, branch_id: 11, entity_id: 21, allowed: true, live_enabled: false, max_messages_per_second: 100 };
    let lease = SessionLease { venue_id: 5, branch_id: 11, epoch: 4, owner_id: "node-a".to_owned(), expires_at_ns: 4_102_444_800_000_000_000, state: SessionState::Ready };
    match authorize(&permission, &lease, 11, 21, live, "node-a", 1_000, 10) {
        Ok(()) => println!("connectivity_authorized:{}", lease_digest(&lease)),
        Err(error) => println!("connectivity_rejected:{error:?}"),
    }
}
