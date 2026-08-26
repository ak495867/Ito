#pragma once

#include "../ito_core/event.hpp"

#include <cstdint>
#include <fstream>
#include <string>

namespace ito::journal {

class JournalFile {
public:
    explicit JournalFile(const std::string& path);
    ~JournalFile();
    bool append(const protocol::EventEnvelope& event);
    bool healthy() const;
    std::uint64_t last_sequence() const;

private:
    std::ofstream stream_;
    std::uint64_t last_sequence_{0};
};

}
