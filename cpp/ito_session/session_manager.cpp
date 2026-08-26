#include "session_manager.hpp"

namespace ito::session {

bool SessionManager::add(std::unique_ptr<connectivity::VenueAdapter> adapter, std::uint64_t now_ns) {
    if (!adapter) {
        return false;
    }
    const auto venue_id = adapter->identity().venue_id;
    if (venue_id == 0 || sessions_.contains(venue_id)) {
        return false;
    }
    sessions_.emplace(venue_id, Entry{std::move(adapter), now_ns});
    return true;
}

bool SessionManager::connect(std::uint16_t venue_id, std::uint64_t now_ns) {
    const auto found = sessions_.find(venue_id);
    if (found == sessions_.end()) {
        return false;
    }
    const auto result = found->second.adapter->connect(now_ns);
    if (result) {
        found->second.last_transition_ns = now_ns;
    }
    return result;
}

bool SessionManager::disconnect(std::uint16_t venue_id, std::uint64_t now_ns) {
    const auto found = sessions_.find(venue_id);
    if (found == sessions_.end()) {
        return false;
    }
    found->second.adapter->disconnect(now_ns);
    found->second.last_transition_ns = now_ns;
    return true;
}

std::optional<connectivity::ExecutionReport> SessionManager::submit(const connectivity::NormalizedOrder& order, std::uint16_t venue_id, std::uint64_t now_ns) {
    const auto found = sessions_.find(venue_id);
    if (found == sessions_.end() || found->second.adapter->status() != connectivity::SessionStatus::Ready) {
        return std::nullopt;
    }
    return found->second.adapter->submit(order, now_ns);
}

std::optional<connectivity::ExecutionReport> SessionManager::cancel(std::uint64_t client_order_id, std::uint16_t venue_id, std::uint64_t now_ns) {
    const auto found = sessions_.find(venue_id);
    if (found == sessions_.end()) {
        return std::nullopt;
    }
    return found->second.adapter->cancel(client_order_id, now_ns);
}

std::vector<SessionStatusView> SessionManager::statuses() const {
    std::vector<SessionStatusView> result;
    result.reserve(sessions_.size());
    for (const auto& [venue_id, entry] : sessions_) {
        const auto identity = entry.adapter->identity();
        result.push_back(SessionStatusView{venue_id, identity.broker_id, entry.adapter->status(), entry.last_transition_ns});
    }
    return result;
}

std::vector<connectivity::ExecutionReport> SessionManager::poll_all(std::uint64_t now_ns) {
    std::vector<connectivity::ExecutionReport> result;
    for (auto& [venue_id, entry] : sessions_) {
        static_cast<void>(venue_id);
        auto reports = entry.adapter->poll(now_ns);
        result.insert(result.end(), reports.begin(), reports.end());
    }
    return result;
}

}
