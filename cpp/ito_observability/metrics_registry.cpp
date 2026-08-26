#include "metrics_registry.hpp"

#include <algorithm>
#include <cmath>

namespace ito::observability {

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
    auto& values = entries_[name].latency_ns;
    values.push_back(latency_ns);
    ++entries_[name].count;
}

MetricSnapshot MetricsRegistry::snapshot(const std::string& name) const {
    std::scoped_lock lock(mutex_);
    const auto found = entries_.find(name);
    if (found == entries_.end()) {
        return {};
    }
    auto values = found->second.latency_ns;
    std::sort(values.begin(), values.end());
    const auto pick = [&values](double fraction) -> std::uint64_t {
        if (values.empty()) return 0;
        const auto index = std::min(values.size() - 1, static_cast<std::size_t>(std::ceil(fraction * static_cast<double>(values.size())) - 1.0));
        return values[index];
    };
    return MetricSnapshot{found->second.count, found->second.errors, found->second.gauge, pick(0.50), pick(0.99)};
}

}
