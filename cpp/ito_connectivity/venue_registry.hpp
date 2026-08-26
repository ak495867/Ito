#pragma once

#include "venue_adapter.hpp"

#include <cstdint>
#include <memory>
#include <optional>
#include <vector>

namespace ito::connectivity {

class VenueRegistry {
public:
    bool register_adapter(std::unique_ptr<VenueAdapter> adapter);
    VenueAdapter* find(std::uint16_t venue_id);
    const VenueAdapter* find(std::uint16_t venue_id) const;
    std::vector<VenueIdentity> identities() const;
    std::size_t size() const;

private:
    std::vector<std::unique_ptr<VenueAdapter>> adapters_;
};

}
