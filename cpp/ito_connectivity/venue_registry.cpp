#include "venue_registry.hpp"

namespace ito::connectivity {

bool VenueRegistry::register_adapter(std::unique_ptr<VenueAdapter> adapter) {
    if (!adapter || adapter->identity().venue_id == 0 || find(adapter->identity().venue_id) != nullptr) {
        return false;
    }
    adapters_.push_back(std::move(adapter));
    return true;
}

VenueAdapter* VenueRegistry::find(std::uint16_t venue_id) {
    for (auto& adapter : adapters_) {
        if (adapter->identity().venue_id == venue_id) {
            return adapter.get();
        }
    }
    return nullptr;
}

const VenueAdapter* VenueRegistry::find(std::uint16_t venue_id) const {
    for (const auto& adapter : adapters_) {
        if (adapter->identity().venue_id == venue_id) {
            return adapter.get();
        }
    }
    return nullptr;
}

std::vector<VenueIdentity> VenueRegistry::identities() const {
    std::vector<VenueIdentity> result;
    result.reserve(adapters_.size());
    for (const auto& adapter : adapters_) {
        result.push_back(adapter->identity());
    }
    return result;
}

std::size_t VenueRegistry::size() const {
    return adapters_.size();
}

}
