#include "../../cpp/ito_journal/journal_file.hpp"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>

int main() {
    const std::string path = "/tmp/ito_journal_file_regression.jsonl";
    std::remove(path.c_str());
    {
        ito::journal::JournalFile journal(path);
        assert(journal.append(ito::protocol::EventEnvelope{1, 1, ito::protocol::EventType::Intent, "quote=\"value\"\nnext"}));
        assert(journal.last_sequence() == 1);
    }
    {
        ito::journal::JournalFile journal(path);
        assert(journal.last_sequence() == 1);
        assert(!journal.append(ito::protocol::EventEnvelope{3, 3, ito::protocol::EventType::Intent, "gap"}));
        assert(journal.append(ito::protocol::EventEnvelope{2, 2, ito::protocol::EventType::Intent, "next"}));
    }
    std::ifstream input(path);
    const std::string content((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    assert(content.find("quote=\\\"value\\\"\\nnext") != std::string::npos);
    std::remove(path.c_str());
    return 0;
}
