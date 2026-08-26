#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

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
};

class EndpointConnector {
public:
    explicit EndpointConnector(EndpointConnectorConfig config);
    ~EndpointConnector();
    EndpointConnector(const EndpointConnector&) = delete;
    EndpointConnector& operator=(const EndpointConnector&) = delete;
    bool open();
    void close();
    bool send(std::string_view bytes);
    std::optional<std::string> receive();
    bool connected() const;

private:
    EndpointConnectorConfig config_;
    int descriptor_{-1};
    ::ssl_ctx_st* tls_context_{nullptr};
    ::ssl_st* tls_session_{nullptr};
};

}
