#include "endpoint_connector.hpp"

#include <algorithm>
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <netdb.h>
#include <openssl/ssl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <chrono>
#include <condition_variable>
#include <deque>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>

namespace ito::connectivity {

namespace {

std::uint32_t le32_to_cpu(const char* bytes) {
    const auto* encoded = reinterpret_cast<const unsigned char*>(bytes);
    return static_cast<std::uint32_t>(encoded[0]) |
           (static_cast<std::uint32_t>(encoded[1]) << 8U) |
           (static_cast<std::uint32_t>(encoded[2]) << 16U) |
           (static_cast<std::uint32_t>(encoded[3]) << 24U);
}

bool verify_message(const char* message, std::size_t length) {
    return message != nullptr && length > 0;
}

}

class EndpointConnector::ConnectionPool {
public:
    explicit ConnectionPool(const EndpointConnectorConfig& config)
        : config_(config) {}

    std::shared_ptr<EndpointConnector> acquire() {
        std::scoped_lock lock(mutex_);
        auto now = std::chrono::steady_clock::now();
        while (!available_.empty()) {
            auto it = available_.front();
            available_.pop_front();
            in_use_.insert(it);
            if (it->connected()) {
                return it;
            }
        }
        if (active_.size() >= config_.max_connections) {
            return nullptr;
        }
        auto connector = std::make_shared<EndpointConnector>(config_);
        active_.insert(connector);
        in_use_.insert(connector);
        if (connector->open()) {
            return connector;
        }
        active_.erase(connector);
        return nullptr;
    }

    void release(std::shared_ptr<EndpointConnector> connector) {
        std::scoped_lock lock(mutex_);
        in_use_.erase(connector);
        if (connector && connector->connected()) {
            available_.push_back(connector);
        } else {
            active_.erase(connector);
            if (connector) {
                auto fresh = std::make_shared<EndpointConnector>(config_);
                active_.insert(fresh);
            }
        }
    }

    std::size_t size() const {
        std::scoped_lock lock(mutex_);
        return active_.size();
    }

    std::size_t available() const {
        std::scoped_lock lock(mutex_);
        return available_.size();
    }

private:
    EndpointConnectorConfig config_;
    mutable std::mutex mutex_;
    std::unordered_set<std::shared_ptr<EndpointConnector>> active_;
    std::unordered_set<std::shared_ptr<EndpointConnector>> in_use_;
    std::deque<std::shared_ptr<EndpointConnector>> available_;
};

static thread_local std::shared_ptr<EndpointConnector::ConnectionPool> g_pool;

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
        int flags = fcntl(candidate, F_GETFL, 0);
        fcntl(candidate, F_SETFL, flags | O_NONBLOCK);
        if (connect(candidate, address->ai_addr, address->ai_addrlen) == 0) {
            descriptor_ = candidate;
            break;
        }
        int err = errno;
        if (err == EINPROGRESS || err == EWOULDBLOCK) {
            fd_set write_fds;
            FD_ZERO(&write_fds);
            FD_SET(candidate, &write_fds);
            timeval tv{};
            tv.tv_sec = config_.connect_timeout_ms / 1000;
            tv.tv_usec = (config_.connect_timeout_ms % 1000) * 1000;
            if (select(candidate + 1, nullptr, &write_fds, nullptr, &tv) > 0) {
                descriptor_ = candidate;
                break;
            }
        }
        ::close(candidate);
    }
    freeaddrinfo(addresses);
    if (!connected()) {
        return false;
    }
    fcntl(descriptor_, F_SETFL, fcntl(descriptor_, F_GETFL, 0) & ~O_NONBLOCK);
    if (!config_.tls_required) {
        return true;
    }
    return establish_tls();
}

bool EndpointConnector::establish_tls() {
    tls_context_ = SSL_CTX_new(TLS_client_method());
    if (!tls_context_) {
        close();
        return false;
    }
    SSL_CTX_set_min_proto_version(tls_context_, TLS1_3_VERSION);
    SSL_CTX_set_verify(tls_context_, SSL_VERIFY_PEER, nullptr);
    SSL_CTX_set_options(tls_context_, SSL_OP_NO_RENEGOTIATION | SSL_OP_SINGLE_DH_USE | SSL_OP_SINGLE_ECDH_USE);
    if (!config_.root_ca_path.empty()) {
        if (SSL_CTX_load_verify_locations(tls_context_, config_.root_ca_path.c_str(), nullptr) != 1) {
            close();
            return false;
        }
    } else if (SSL_CTX_set_default_verify_paths(tls_context_) != 1) {
        close();
        return false;
    }
    if (!config_.client_cert_path.empty() || !config_.client_key_path.empty()) {
        if (SSL_CTX_use_certificate_file(tls_context_, config_.client_cert_path.c_str(), SSL_FILETYPE_PEM) != 1 ||
            SSL_CTX_use_PrivateKey_file(tls_context_, config_.client_key_path.c_str(), SSL_FILETYPE_PEM) != 1 ||
            SSL_CTX_check_private_key(tls_context_) != 1) {
            close();
            return false;
        }
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
        shutdown(descriptor_, SHUT_RDWR);
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
    if (received < 4) {
        return std::nullopt;
    }
    const auto length = le32_to_cpu(buffer);
    if (length > sizeof(buffer) - 4 || received != length + 4) {
        return std::nullopt;
    }
    if (!verify_message(buffer + 4, length)) {
        return std::nullopt;
    }
    return std::string(buffer + 4, static_cast<std::size_t>(length));
}

bool EndpointConnector::connected() const {
    return descriptor_ >= 0;
}

std::uint64_t EndpointConnector::last_error_code() const {
    return last_error_code_;
}

std::shared_ptr<EndpointConnector> EndpointConnector::acquire(const EndpointConnectorConfig& config) {
    if (!g_pool) {
        g_pool = std::make_shared<ConnectionPool>(config);
    }
    return g_pool->acquire();
}

void EndpointConnector::release(std::shared_ptr<EndpointConnector> connector) {
    if (g_pool) {
        g_pool->release(connector);
    }
}

std::size_t EndpointConnector::pool_size() {
    if (g_pool) {
        return g_pool->size();
    }
    return 0;
}

bool EndpointConnector::attempt_connect() {
    return open();
}

bool EndpointConnector::wait_readable(std::uint64_t timeout_ms) {
    if (!connected()) return false;
    fd_set read_fds;
    FD_ZERO(&read_fds);
    FD_SET(descriptor_, &read_fds);
    timeval tv{};
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    return select(descriptor_ + 1, &read_fds, nullptr, nullptr, &tv) > 0;
}

bool EndpointConnector::wait_writable(std::uint64_t timeout_ms) {
    if (!connected()) return false;
    fd_set write_fds;
    FD_ZERO(&write_fds);
    FD_SET(descriptor_, &write_fds);
    timeval tv{};
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    return select(descriptor_ + 1, nullptr, &write_fds, nullptr, &tv) > 0;
}

}