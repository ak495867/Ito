#include "lease_fencer.hpp"

namespace ito::session {

bool LeaseFencer::acquire(std::uint16_t venue_id, std::uint64_t branch_id, std::string owner_id, std::uint64_t now_ns, std::uint64_t ttl_ns) {
    if (venue_id == 0 || branch_id == 0 || owner_id.empty() || ttl_ns == 0 || (current_.expires_at_ns > now_ns && !current_.owner_id.empty())) {
        return false;
    }
    ++current_.epoch;
    current_.venue_id = venue_id;
    current_.branch_id = branch_id;
    current_.owner_id = std::move(owner_id);
    current_.expires_at_ns = now_ns + ttl_ns;
    return true;
}

bool LeaseFencer::renew(const std::string& owner_id, std::uint64_t now_ns, std::uint64_t ttl_ns) {
    if (owner_id.empty() || owner_id != current_.owner_id || current_.expires_at_ns <= now_ns || ttl_ns == 0) {
        return false;
    }
    current_.expires_at_ns = now_ns + ttl_ns;
    return true;
}

bool LeaseFencer::release(const std::string& owner_id) {
    if (owner_id.empty() || owner_id != current_.owner_id) {
        return false;
    }
    current_.expires_at_ns = 0;
    current_.owner_id.clear();
    return true;
}

bool LeaseFencer::owns(std::uint16_t venue_id, std::uint64_t branch_id, const std::string& owner_id, std::uint64_t now_ns) const {
    return current_.venue_id == venue_id && current_.branch_id == branch_id && current_.owner_id == owner_id && current_.expires_at_ns > now_ns;
}

const Lease& LeaseFencer::current() const {
    return current_;
}

}
