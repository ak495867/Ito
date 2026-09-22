#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

struct ssl_ctx_st;
struct ssl_st;

namespace ito::connectivity {

struct EndpointConnectorConfig {
    std::string host;
    std::uint16_t port{};
    bool tls_required{true};
    bool live_enabled{false};
    std::string root_ca_path;
    std::string client_cert_path;
    std::string client_key_path;
    std::uint64_t connect_timeout_ms{5000};
    std::uint64_t read_timeout_ms{30000};
    std::uint64_t write_timeout_ms{30000};
    std::uint32_t max_retries{3};
    std::uint64_t retry_backoff_ms{100};
    bool enable_connection_pool{true};
    std::size_t max_connections{10};
};

class EndpointConnector {
public:
    class ConnectionPool;

    explicit EndpointConnector(EndpointConnectorConfig config);
    ~EndpointConnector();
    EndpointConnector(const EndpointConnector&) = delete;
    EndpointConnector& operator=(const EndpointConnector&) = delete;
    bool open();
    void close();
    bool send(std::string_view bytes);
    std::optional<std::string> receive();
    bool connected() const;
    std::uint64_t last_error_code() const;

    static std::shared_ptr<EndpointConnector> acquire(const EndpointConnectorConfig& config);
    static void release(std::shared_ptr<EndpointConnector> connector);
    static std::size_t pool_size();

private:
    bool attempt_connect();
    bool establish_tls();
    void close_socket();
    void close_tls();
    bool wait_readable(std::uint64_t timeout_ms);
    bool wait_writable(std::uint64_t timeout_ms);

    EndpointConnectorConfig config_;
    int descriptor_{-1};
    ::ssl_ctx_st* tls_context_{nullptr};
    ::ssl_st* tls_session_{nullptr};
    std::uint64_t last_error_code_{0};
};

}
