#pragma once

#include <cstdint>
#include <string>

namespace ito::session {

struct Lease {
    std::uint16_t venue_id{};
    std::uint64_t branch_id{};
    std::uint64_t epoch{};
    std::string owner_id;
    std::uint64_t expires_at_ns{};
};

class LeaseFencer {
public:
    bool acquire(std::uint16_t venue_id, std::uint64_t branch_id, std::string owner_id, std::uint64_t now_ns, std::uint64_t ttl_ns);
    bool renew(const std::string& owner_id, std::uint64_t now_ns, std::uint64_t ttl_ns);
    bool release(const std::string& owner_id);
    bool owns(std::uint16_t venue_id, std::uint64_t branch_id, const std::string& owner_id, std::uint64_t now_ns) const;
    const Lease& current() const;

private:
    Lease current_{};
};

}
