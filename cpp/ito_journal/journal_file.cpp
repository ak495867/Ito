#include "journal_file.hpp"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <utility>

namespace {
std::string escape_json(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size());
    for (const auto character : value) {
        switch (character) {
            case '\\': escaped += "\\\\"; break;
            case '"': escaped += "\\\""; break;
            case '\b': escaped += "\\b"; break;
            case '\f': escaped += "\\f"; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default:
                if (static_cast<unsigned char>(character) < 0x20) {
                    std::ostringstream code;
                    code << "\\\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(static_cast<unsigned char>(character));
                    escaped += code.str();
                } else {
                    escaped.push_back(character);
                }
        }
    }
    return escaped;
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
    stream_ << "{\"event_id\":" << event.event_id << ",\"sequence\":" << event.sequence << ",\"event_type\":" << static_cast<unsigned>(event.type) << ",\"payload\":\"" << escape_json(event.payload) << "\"}\n";
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
