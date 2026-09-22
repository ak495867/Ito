#pragma once

#include "../../interfaces/schemas/ito_protocol.hpp"

#include <cstdint>
#include <fstream>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace ito::reference {

class JournalFile {
public:
    explicit JournalFile(const std::string& path);
    ~JournalFile();

    bool append(const protocol::EventEnvelope& event);
    bool healthy() const;
    std::uint64_t last_sequence() const;
    std::optional<std::vector<protocol::EventEnvelope>> load(std::uint64_t from_sequence = 0) const;
    void rotate();
    std::size_t file_size() const;

private:
    bool write_header();
    bool read_header();
    bool verify_integrity();

    std::string path_;
    mutable std::mutex mutex_;
    std::ofstream stream_;
    std::uint64_t last_sequence_{0};
    bool initialized_{false};
    static constexpr std::uint64_t kMaxFileSize = 1024ULL * 1024ULL * 256;
    static constexpr std::uint32_t kMagic = 0x4A4F5552;
};

class JournalManager {
public:
    explicit JournalManager(const std::string& base_path);
    ~JournalManager();

    bool append(const protocol::EventEnvelope& event);
    std::optional<std::vector<protocol::EventEnvelope>> load_recent(std::uint64_t count) const;
    std::uint64_t last_sequence() const;
    bool rotate_all();
    bool verify_all();

private:
    std::string base_path_;
    std::vector<std::unique_ptr<JournalFile>> journals_;
    mutable std::mutex mutex_;
};

}