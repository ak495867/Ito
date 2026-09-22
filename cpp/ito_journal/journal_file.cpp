#include "journal_file.hpp"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <utility>

namespace {
void write_escaped_json(std::ostream& stream, const std::string& value) {
    bool needs_escape = false;
    for (const char c : value) {
        if (c == '\\' || c == '"' || static_cast<unsigned char>(c) < 0x20) {
            needs_escape = true;
            break;
        }
    }
    if (!needs_escape) {
        stream << value;
        return;
    }
    for (const char character : value) {
        switch (character) {
            case '\\': stream << "\\\\"; break;
            case '"': stream << "\\\""; break;
            case '\b': stream << "\\b"; break;
            case '\f': stream << "\\f"; break;
            case '\n': stream << "\\n"; break;
            case '\r': stream << "\\r"; break;
            case '\t': stream << "\\t"; break;
            default:
                if (static_cast<unsigned char>(character) < 0x20) {
                    stream << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(static_cast<unsigned char>(character)) << std::dec;
                } else {
                    stream.put(character);
                }
        }
    }
}
}

namespace ito::journal {

JournalFile::JournalFile(const std::string& path) : stream_(path, std::ios::out | std::ios::app) {
    std::ifstream existing(path);
    std::string line;
    while (std::getline(existing, line)) {
        const auto marker = line.find("\"sequence\":");
        if (marker == std::string::npos) {
            continue;
        }
        try {
            last_sequence_ = std::stoull(line.substr(marker + 11));
        } catch (...) {
            stream_.setstate(std::ios::failbit);
            break;
        }
    }
}

JournalFile::~JournalFile() {
    stream_.flush();
}

bool JournalFile::append(const protocol::EventEnvelope& event) {
    if (!stream_.good() || event.sequence != last_sequence_ + 1) {
        return false;
    }
    stream_ << "{\"event_id\":" << event.event_id << ",\"sequence\":" << event.sequence << ",\"event_type\":" << static_cast<unsigned>(event.type) << ",\"payload\":\"";
    write_escaped_json(stream_, event.payload);
    stream_ << "\"}\n";
    stream_.flush();
    if (!stream_.good()) {
        return false;
    }
    last_sequence_ = event.sequence;
    return true;
}

bool JournalFile::healthy() const {
    return stream_.good();
}

std::uint64_t JournalFile::last_sequence() const {
    return last_sequence_;
}

}
