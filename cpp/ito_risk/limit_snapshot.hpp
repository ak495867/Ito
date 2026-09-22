#pragma once

#include "../../interfaces/schemas/ito_protocol.hpp"

#include <cstdint>
#include <string>

namespace ito::risk {

using LimitSnapshot = protocol::LimitSnapshot;

class LimitSnapshotGuard {
public:
    bool activate(LimitSnapshot snapshot, std::uint64_t now_ns);
    bool valid(std::uint64_t now_ns) const;
    const LimitSnapshot& active() const;
    std::string status(std::uint64_t now_ns) const;

private:
    LimitSnapshot active_{};
    bool initialized_{false};
};

}
