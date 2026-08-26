#include "endpoint_connector.hpp"

#include <arpa/inet.h>
#include <netdb.h>
#include <openssl/ssl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <string>
#include <utility>

namespace ito::connectivity {

EndpointConnector::EndpointConnector(EndpointConnectorConfig config) : config_(std::move(config)) {}

EndpointConnector::~EndpointConnector() {
    close();
}

bool EndpointConnector::open() {
    if (!config_.live_enabled || !config_.tls_required || connected()) {
        return false;
    }
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* addresses = nullptr;
    const auto port = std::to_string(config_.port);
    if (getaddrinfo(config_.host.c_str(), port.c_str(), &hints, &addresses) != 0) {
        return false;
    }
    for (auto* address = addresses; address != nullptr; address = address->ai_next) {
        const auto candidate = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
        if (candidate < 0) {
            continue;
        }
        if (connect(candidate, address->ai_addr, address->ai_addrlen) == 0) {
            descriptor_ = candidate;
            break;
        }
        ::close(candidate);
    }
    freeaddrinfo(addresses);
    if (!connected()) {
        return false;
    }
    if (!config_.tls_required) {
        return true;
    }
    tls_context_ = SSL_CTX_new(TLS_client_method());
    if (!tls_context_) {
        close();
        return false;
    }
    SSL_CTX_set_min_proto_version(tls_context_, TLS1_3_VERSION);
    SSL_CTX_set_verify(tls_context_, SSL_VERIFY_PEER, nullptr);
    if (!config_.root_ca_path.empty()) {
        if (SSL_CTX_load_verify_locations(tls_context_, config_.root_ca_path.c_str(), nullptr) != 1) {
            close();
            return false;
        }
    } else if (SSL_CTX_set_default_verify_paths(tls_context_) != 1) {
        close();
        return false;
    }
    if (config_.client_cert_path.empty() || config_.client_key_path.empty() || SSL_CTX_use_certificate_file(tls_context_, config_.client_cert_path.c_str(), SSL_FILETYPE_PEM) != 1 || SSL_CTX_use_PrivateKey_file(tls_context_, config_.client_key_path.c_str(), SSL_FILETYPE_PEM) != 1 || SSL_CTX_check_private_key(tls_context_) != 1) {
        close();
        return false;
    }
    tls_session_ = SSL_new(tls_context_);
    if (!tls_session_) {
        close();
        return false;
    }
    SSL_set_tlsext_host_name(tls_session_, config_.host.c_str());
    SSL_set1_host(tls_session_, config_.host.c_str());
    SSL_set_fd(tls_session_, descriptor_);
    if (SSL_connect(tls_session_) != 1) {
        close();
        return false;
    }
    return true;
}

void EndpointConnector::close() {
    if (tls_session_) {
        SSL_shutdown(tls_session_);
        SSL_free(tls_session_);
        tls_session_ = nullptr;
    }
    if (tls_context_) {
        SSL_CTX_free(tls_context_);
        tls_context_ = nullptr;
    }
    if (descriptor_ >= 0) {
        ::close(descriptor_);
        descriptor_ = -1;
    }
}

bool EndpointConnector::send(std::string_view bytes) {
    if (!connected()) {
        return false;
    }
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        const auto sent = tls_session_ ? SSL_write(tls_session_, bytes.data() + offset, static_cast<int>(bytes.size() - offset)) : ::send(descriptor_, bytes.data() + offset, bytes.size() - offset, MSG_NOSIGNAL);
        if (sent <= 0) {
            close();
            return false;
        }
        offset += static_cast<std::size_t>(sent);
    }
    return true;
}

std::optional<std::string> EndpointConnector::receive() {
    if (!connected()) {
        return std::nullopt;
    }
    char buffer[4096];
    const auto received = tls_session_ ? SSL_read(tls_session_, buffer, sizeof(buffer)) : ::recv(descriptor_, buffer, sizeof(buffer), MSG_DONTWAIT);
    if (received <= 0) {
        return std::nullopt;
    }
    return std::string(buffer, static_cast<std::size_t>(received));
}

bool EndpointConnector::connected() const {
    return descriptor_ >= 0;
}

}
