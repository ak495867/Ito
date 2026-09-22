#include "metrics_registry.hpp"

#include <bit>
#include <cmath>

namespace ito::observability {

namespace {
inline std::size_t latency_bucket(std::uint64_t latency_ns) {
    if (latency_ns == 0) return 0;
    std::size_t bucket = 64 - static_cast<std::size_t>(std::countl_zero(latency_ns));
    return bucket < 64 ? bucket : 63;
}
}

void MetricsRegistry::increment(const std::string& name, std::uint64_t value) {
    std::scoped_lock lock(mutex_);
    entries_[name].count += value;
}

void MetricsRegistry::error(const std::string& name) {
    std::scoped_lock lock(mutex_);
    ++entries_[name].errors;
}

void MetricsRegistry::gauge(const std::string& name, std::int64_t value) {
    std::scoped_lock lock(mutex_);
    entries_[name].gauge = value;
}

void MetricsRegistry::observe_latency(const std::string& name, std::uint64_t latency_ns) {
    std::scoped_lock lock(mutex_);
    auto& entry = entries_[name];
    entry.buckets[latency_bucket(latency_ns)]++;
    ++entry.count;
    ++entry.observation_count;
}

MetricSnapshot MetricsRegistry::snapshot(const std::string& name) const {
    std::scoped_lock lock(mutex_);
    const auto found = entries_.find(name);
    if (found == entries_.end()) {
        return {};
    }
    const auto& entry = found->second;
    const auto pick = [&](double fraction) -> std::uint64_t {
        if (entry.observation_count == 0) return 0;
        std::uint64_t target = static_cast<std::uint64_t>(std::ceil(fraction * static_cast<double>(entry.observation_count)));
        std::uint64_t sum = 0;
        for (std::size_t i = 0; i < 64; ++i) {
            sum += entry.buckets[i];
            if (sum >= target) {
                return (1ULL << i);
            }
        }
        return 0;
    };
    return MetricSnapshot{entry.count, entry.errors, entry.observation_count, entry.gauge, pick(0.50), pick(0.99)};
}

}
