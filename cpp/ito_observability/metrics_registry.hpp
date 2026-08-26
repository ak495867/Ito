#pragma once

#include <cstdint>
#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace ito::observability {

struct MetricSnapshot {
    std::uint64_t count{};
    std::uint64_t errors{};
    std::int64_t gauge{};
    std::uint64_t p50_ns{};
    std::uint64_t p99_ns{};
};

class MetricsRegistry {
public:
    void increment(const std::string& name, std::uint64_t value = 1);
    void error(const std::string& name);
    void gauge(const std::string& name, std::int64_t value);
    void observe_latency(const std::string& name, std::uint64_t latency_ns);
    MetricSnapshot snapshot(const std::string& name) const;

private:
    struct Entry {
        std::uint64_t count{};
        std::uint64_t errors{};
        std::int64_t gauge{};
        std::vector<std::uint64_t> latency_ns;
    };
    mutable std::mutex mutex_;
    std::map<std::string, Entry> entries_;
};

}
