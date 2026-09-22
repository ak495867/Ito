#include "journal_file.hpp"

#include <algorithm>
#include <filesystem>
#include <iostream>

namespace ito::reference {

namespace {
constexpr std::size_t kHeaderSize = 16;
constexpr std::uint32_t kCurrentVersion = 1;
}

JournalFile::JournalFile(const std::string& path) : path_(path) {
    std::filesystem::create_directories(std::filesystem::path(path).parent_path());
    stream_.open(path, std::ios::binary | std::ios::in | std::ios::out | std::ios::app);
    if (!stream_.is_open()) {
        stream_.open(path, std::ios::binary | std::ios::out | std::ios::trunc);
        if (stream_.is_open()) {
            write_header();
        }
    } else {
        read_header();
    }
    initialized_ = stream_.is_open();
}

JournalFile::~JournalFile() {
    if (stream_.is_open()) {
        stream_.close();
    }
}

bool JournalFile::write_header() {
    if (!stream_.is_open()) return false;
    std::array<std::uint8_t, kHeaderSize> header{};
    header[0] = static_cast<std::uint8_t>(kMagic & 0xFF);
    header[1] = static_cast<std::uint8_t>((kMagic >> 8) & 0xFF);
    header[2] = static_cast<std::uint8_t>((kMagic >> 16) & 0xFF);
    header[3] = static_cast<std::uint8_t>((kMagic >> 24) & 0xFF);
    header[4] = static_cast<std::uint8_t>(kCurrentVersion & 0xFF);
    header[5] = static_cast<std::uint8_t>((kCurrentVersion >> 8) & 0xFF);
    auto pos = stream_.tellp();
    stream_.seekp(0);
    stream_.write(reinterpret_cast<const char*>(header.data()), kHeaderSize);
    stream_.seekp(pos);
    return true;
}

bool JournalFile::read_header() {
    if (!stream_.is_open()) return false;
    auto pos = stream_.tellg();
    stream_.seekg(0);
    std::array<std::uint8_t, kHeaderSize> header{};
    stream_.read(reinterpret_cast<char*>(header.data()), kHeaderSize);
    stream_.seekg(pos);
    std::uint32_t magic = 0;
    for (int i = 0; i < 4; ++i) {
        magic |= static_cast<std::uint32_t>(header[i]) << (8 * i);
    }
    if (magic != kMagic) return false;
    std::uint32_t version = static_cast<std::uint32_t>(header[4]) | (static_cast<std::uint32_t>(header[5]) << 8);
    if (version != kCurrentVersion) return false;
    return true;
}

bool JournalFile::verify_integrity() {
    if (!stream_.is_open()) return false;
    auto pos = stream_.tellg();
    stream_.seekg(0, std::ios::end);
    auto size = stream_.tellg();
    stream_.seekg(pos);
    return size >= static_cast<std::streamoff>(kHeaderSize);
}

bool JournalFile::append(const protocol::EventEnvelope& event) {
    std::scoped_lock lock(mutex_);
    if (!initialized_ || !stream_.is_open()) return false;

    std::string serialized = event.payload;
    std::uint64_t record_size = serialized.size();
    if (record_size > 0xFFFFFFFFULL) return false;

    std::array<std::uint8_t, 8> size_bytes{};
    for (int i = 0; i < 8; ++i) {
        size_bytes[i] = static_cast<std::uint8_t>((record_size >> (8 * i)) & 0xFF);
    }

    auto current_pos = stream_.tellp();
    if (current_pos >= static_cast<std::streamoff>(kMaxFileSize)) {
        return false;
    }

    stream_.write(reinterpret_cast<const char*>(size_bytes.data()), 8);
    stream_.write(reinterpret_cast<const char*>(&event.event_id), sizeof(event.event_id));
    stream_.write(reinterpret_cast<const char*>(&event.sequence), sizeof(event.sequence));
    stream_.write(reinterpret_cast<const char*>(&event.type), sizeof(event.type));
    stream_.write(reinterpret_cast<const char*>(&event.correlation_id), sizeof(event.correlation_id));
    stream_.write(reinterpret_cast<const char*>(event.payload.data()), static_cast<std::streamsize>(event.payload.size()));
    stream_.flush();
    last_sequence_ = event.sequence;
    return true;
}

bool JournalFile::healthy() const {
    if (!initialized_ || !stream_.is_open()) return false;
    std::scoped_lock lock(mutex_);
    return verify_integrity();
}

std::uint64_t JournalFile::last_sequence() const {
    std::scoped_lock lock(mutex_);
    return last_sequence_;
}

std::optional<std::vector<protocol::EventEnvelope>> JournalFile::load(std::uint64_t from_sequence) const {
    std::scoped_lock lock(mutex_);
    if (!initialized_ || !stream_.is_open()) return std::nullopt;

    std::vector<protocol::EventEnvelope> events;
    auto pos = stream_.tellg();
    stream_.seekg(0);

    std::array<std::uint8_t, kHeaderSize> header{};
    stream_.read(reinterpret_cast<char*>(header.data()), kHeaderSize);

    while (stream_.good()) {
        std::array<std::uint8_t, 8> size_bytes{};
        stream_.read(reinterpret_cast<char*>(size_bytes.data()), 8);
        if (stream_.gcount() < 8) break;

        std::uint64_t record_size = 0;
        for (int i = 0; i < 8; ++i) {
            record_size |= static_cast<std::uint64_t>(size_bytes[i]) << (8 * i);
        }

        if (record_size == 0 || record_size > 0xFFFFFFFFULL) break;

        std::vector<std::uint8_t> buffer(record_size);
        stream_.read(reinterpret_cast<char*>(buffer.data()), static_cast<std::streamsize>(record_size));
        if (stream_.gcount() != static_cast<std::streamsize>(record_size)) break;

        protocol::EventEnvelope event{};
        std::size_t offset = 0;
        std::memcpy(&event.event_id, buffer.data() + offset, sizeof(event.event_id));
        offset += sizeof(event.event_id);
        std::memcpy(&event.sequence, buffer.data() + offset, sizeof(event.sequence));
        offset += sizeof(event.sequence);
        std::memcpy(&event.type, buffer.data() + offset, sizeof(event.type));
        offset += sizeof(event.type);
        std::memcpy(&event.correlation_id, buffer.data() + offset, sizeof(event.correlation_id));
        offset += sizeof(event.correlation_id);
        event.payload = std::string(buffer.data() + offset, buffer.data() + record_size);

        if (event.sequence >= from_sequence) {
            events.push_back(std::move(event));
        }
    }

    stream_.seekg(pos);
    return events;
}

void JournalFile::rotate() {
    std::scoped_lock lock(mutex_);
    if (stream_.is_open()) {
        stream_.close();
    }
    std::filesystem::path p(path_);
    std::string rotated = (p.parent_path() / (p.stem().string() + ".rot")).string();
    std::filesystem::rename(p, std::filesystem::path(rotated));
    stream_.open(path_, std::ios::binary | std::ios::out | std::ios::trunc);
    if (stream_.is_open()) {
        write_header();
        last_sequence_ = 0;
    }
}

std::size_t JournalFile::file_size() const {
    std::scoped_lock lock(mutex_);
    if (!stream_.is_open()) return 0;
    auto pos = stream_.tellp();
    return static_cast<std::size_t>(pos);
}

}