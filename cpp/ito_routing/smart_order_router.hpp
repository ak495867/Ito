#pragma once

#include "../ito_connectivity/venue_types.hpp"
#include "../ito_session/session_manager.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <optional>
#include <vector>

namespace ito::routing {

template <typename T, std::size_t Capacity = 1024>
class SpscRingBuffer {
public:
    static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be a power of 2");

    bool push(const T& item) {
        const auto current_tail = tail_.load(std::memory_order_relaxed);
        const auto current_head = head_.load(std::memory_order_acquire);
        if (current_tail - current_head >= Capacity) {
            return false;
        }
        buffer_[current_tail & kMask] = item;
        tail_.store(current_tail + 1, std::memory_order_release);
        return true;
    }

    bool pop(T& item) {
        const auto current_head = head_.load(std::memory_order_relaxed);
        const auto current_tail = tail_.load(std::memory_order_acquire);
        if (current_head == current_tail) {
            return false;
        }
        item = buffer_[current_head & kMask];
        head_.store(current_head + 1, std::memory_order_release);
        return true;
    }

    bool empty() const {
        return head_.load(std::memory_order_relaxed) == tail_.load(std::memory_order_relaxed);
    }

    std::size_t size() const {
        const auto head = head_.load(std::memory_order_relaxed);
        const auto tail = tail_.load(std::memory_order_relaxed);
        return tail >= head ? tail - head : 0;
    }

private:
    static constexpr std::size_t kMask = Capacity - 1;
    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
    std::array<T, Capacity> buffer_{};
};

struct RouteCandidate {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    std::int64_t executable_price_ticks{};
    std::int64_t displayed_quantity{};
    std::uint32_t fee_bps{};
    std::uint32_t rank{};
    bool enabled{};
    bool authorized{};
    bool lease_valid{};
};

struct RoutingPolicy {
    std::uint32_t max_fee_bps{100};
    std::int64_t max_price_deviation_ticks{500};
    bool allow_broker_fallback{true};
};

struct RouteDecision {
    std::uint16_t venue_id{};
    std::uint16_t broker_id{};
    std::int64_t price_ticks{};
    std::uint32_t fee_bps{};
    std::uint32_t rank{};
};

struct RoutedExecution {
    RouteDecision route;
    connectivity::ExecutionReport report;
};

class SmartOrderRouter {
public:
    SmartOrderRouter(session::SessionManager& sessions, RoutingPolicy policy);
    std::vector<RouteDecision> rank(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates) const;
    std::optional<RoutedExecution> submit(const connectivity::NormalizedOrder& order, const std::vector<RouteCandidate>& candidates, std::uint64_t now_ns);

private:
    session::SessionManager& sessions_;
    RoutingPolicy policy_;
};

}
