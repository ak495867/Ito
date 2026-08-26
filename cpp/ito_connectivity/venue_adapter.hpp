#pragma once

#include "venue_types.hpp"

#include <cstdint>
#include <optional>
#include <vector>

namespace ito::connectivity {

class VenueAdapter {
public:
    virtual ~VenueAdapter() = default;
    virtual VenueIdentity identity() const = 0;
    virtual SessionStatus status() const = 0;
    virtual bool connect(std::uint64_t now_ns) = 0;
    virtual void disconnect(std::uint64_t now_ns) = 0;
    virtual std::optional<ExecutionReport> submit(const NormalizedOrder& order, std::uint64_t now_ns) = 0;
    virtual std::optional<ExecutionReport> cancel(std::uint64_t client_order_id, std::uint64_t now_ns) = 0;
    virtual std::vector<ExecutionReport> poll(std::uint64_t now_ns) = 0;
};

}
